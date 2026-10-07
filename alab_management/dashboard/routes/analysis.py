"""Analysis Data API: the HTTP edge an offline analysis service writes its results back through.

Decision D7 in alab_one's ``docs/data-architecture.md`` says an analysis service consumes artifacts via cloud/API
and writes results back *through AlabOS* onto the sample, rather than opening Mongo itself. D9 says AlabOS's own
workers keep their in-process access and HTTP exists only at the edge, with both calling one implementation. These
routes are therefore a thin adapter over ``alab_management.sample_view.analysis_view.AnalysisView``; all the rules
live there and an in-process caller gets exactly the same behaviour.

The three things an analysis worker needs each cycle::

    GET  /api/analysis/pending?kind=&data_source=&params_hash=[&limit=&owner=&include_errors=&include_claimed=]
    POST /api/analysis/claim/<sample_id>            {"kind", "owner"[, "ttl_s"]}        (also renews)
    POST /api/analysis/claim/<sample_id>/release    {"kind", "owner"}
    POST /api/analysis/results/<sample_id>          {"kind", "result"[, "owner", "release_claim",
                                                     "mirror_completed"]}

Status codes: 200 on success, 400 for any validation problem, 401 for a bad token, 404 when the sample id does not
exist, 409 when another worker holds the claim.

Authentication is an optional shared token, off unless the deployment sets one (see ``_configured_token``).
"""

from __future__ import annotations

import hmac
import os
from typing import Any

from bson import ObjectId  # type: ignore
from bson.errors import InvalidId  # type: ignore
from flask import Blueprint, jsonify, request

from alab_management.config import AlabOSConfig
from alab_management.dashboard.lab_views import analysis_view
from alab_management.sample_view.analysis_view import (
    DEFAULT_CLAIM_TTL_S,
    DEFAULT_PENDING_LIMIT,
    SampleNotFoundError,
    input_data_sources,
)
from alab_management.utils.data_objects import make_jsonable

analysis_bp = Blueprint("/analysis", __name__, url_prefix="/api/analysis")

TOKEN_HEADER = "X-AlabOS-Token"
TOKEN_ENV = "ALABOS_DATA_API_TOKEN"


def _configured_token() -> str | None:
    """The shared token this deployment requires, or None when the check is off (the default).

    Either the ``ALABOS_DATA_API_TOKEN`` environment variable or ``[data_api] token`` in the AlabOS config file, so
    turning the check on, or rotating the token, needs no code change. The value is only ever compared, never
    logged, echoed in a response, or included in an error message. A deployment with no readable config file has
    no token and so no check, which is the same default as a deployment that simply did not set one.
    """
    token = os.environ.get(TOKEN_ENV)
    if token:
        return token
    try:
        section = AlabOSConfig().get("data_api") or {}
    except FileNotFoundError:
        return None
    return section.get("token") or None


def _token_bytes(value: str) -> bytes:
    """Bytes for a constant-time compare.

    ``hmac.compare_digest`` raises ``TypeError`` on a ``str`` with non-ASCII characters, and an HTTP header can
    carry any byte, so comparing bytes is what makes a non-ASCII token answer 401 instead of crashing the request.
    """
    return value.encode("utf-8", "surrogateescape")


@analysis_bp.before_request
def _require_token():
    expected = _configured_token()
    if expected is None:
        return None
    if hmac.compare_digest(
        _token_bytes(request.headers.get(TOKEN_HEADER, "")), _token_bytes(expected)
    ):
        return None
    # Deliberately generic: neither the configured token nor what the caller sent is echoed back.
    return jsonify({"status": "error", "errors": "missing or invalid API token"}), 401


def _body() -> dict[str, Any]:
    body = request.get_json(force=True, silent=True)
    if not isinstance(body, dict):
        raise ValueError("request body must be a JSON object")
    return body


def _sample_object_id(sample_id: str) -> ObjectId:
    try:
        return ObjectId(sample_id)
    except (InvalidId, TypeError) as exception:
        raise ValueError(f"{sample_id!r} is not a valid sample id") from exception


def _flag(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("1", "true", "yes")


def _missing(exception: SampleNotFoundError):
    return jsonify({"status": "error", "errors": str(exception)}), 404


def _invalid(exception: ValueError):
    return jsonify({"status": "error", "errors": str(exception)}), 400


@analysis_bp.route("/pending", methods=["GET"])
def list_pending():
    """Samples with input data for one technique but no result matching the caller's ``params_hash``.

    One call answers the whole question an analysis worker asks each cycle. ``data_source`` names where the input
    data lives, because that differs per lab (alab_one keeps a parsed pattern in ``metadata.diffraction_results``,
    GPSS keeps the ``.xrdml`` in ``metadata.xrd_measurement``); the names and their queries are fixed server-side,
    so no Mongo filter crosses the network.
    """
    try:
        samples = analysis_view.pending_samples(
            kind=request.args.get("kind", ""),
            data_source=request.args.get("data_source", ""),
            params_hash=request.args.get("params_hash", ""),
            limit=int(request.args.get("limit", DEFAULT_PENDING_LIMIT)),
            owner=request.args.get("owner") or None,
            include_errors=_flag(request.args.get("include_errors")),
            include_claimed=_flag(request.args.get("include_claimed")),
        )
    except ValueError as exception:
        return _invalid(exception)

    return jsonify(
        make_jsonable(
            {
                "status": "success",
                "data": {
                    "kind": request.args.get("kind"),
                    "data_source": request.args.get("data_source"),
                    "params_hash": request.args.get("params_hash"),
                    "samples": samples,
                },
            }
        )
    )


@analysis_bp.route("/claim/<sample_id>", methods=["POST"])
def claim_sample(sample_id: str):
    """Take or renew one worker's claim on one sample's analysis kind.

    A repeat call from the same owner is the heartbeat. Nothing has to clean up after a worker that dies: the claim
    carries its own ``expires_at`` and is claimable by anyone once that passes.
    """
    held = None
    try:
        body = _body()
        kind = body.get("kind", "")
        object_id = _sample_object_id(sample_id)
        claim = analysis_view.claim(
            sample_id=object_id,
            kind=kind,
            owner=body.get("owner", ""),
            ttl_s=float(body.get("ttl_s", DEFAULT_CLAIM_TTL_S)),
        )
        if claim is None:
            held = analysis_view.get_claim(object_id, kind)
    except SampleNotFoundError as exception:
        return _missing(exception)
    except ValueError as exception:
        return _invalid(exception)

    if claim is None:
        return (
            jsonify(
                make_jsonable(
                    {
                        "status": "error",
                        "errors": "sample is claimed by another worker",
                        "data": {"claim": held},
                    }
                )
            ),
            409,
        )
    return jsonify(make_jsonable({"status": "success", "data": {"claim": claim}}))


@analysis_bp.route("/claim/<sample_id>/release", methods=["POST"])
def release_sample(sample_id: str):
    """Give up a claim this worker holds. Releasing a claim someone else took over is not an error."""
    try:
        body = _body()
        released = analysis_view.release(
            sample_id=_sample_object_id(sample_id),
            kind=body.get("kind", ""),
            owner=body.get("owner", ""),
        )
    except SampleNotFoundError as exception:
        return _missing(exception)
    except ValueError as exception:
        return _invalid(exception)

    return jsonify({"status": "success", "data": {"released": released}})


@analysis_bp.route("/results/<sample_id>", methods=["POST"])
def write_result(sample_id: str):
    """Write ``metadata.analysis.<kind>`` on one sample, additively, through ``AnalysisView``.

    With ``owner``, the result is only stored while that worker still holds the claim, and the claim is released in
    the same update; the response then says ``written: false`` with HTTP 409 if the claim had been taken over.
    ``mirrored`` reports whether the same key was also set on the sample's archived copy in the completed
    database, which is false for a sample that was never archived and for ``mirror_completed: false``.
    """
    try:
        body = _body()
        outcome = analysis_view.write_result(
            sample_id=_sample_object_id(sample_id),
            kind=body.get("kind", ""),
            result=body.get("result"),
            owner=body.get("owner") or None,
            release_claim=_flag(body.get("release_claim"), default=True),
            mirror_completed=_flag(body.get("mirror_completed"), default=True),
        )
    except SampleNotFoundError as exception:
        return _missing(exception)
    except ValueError as exception:
        return _invalid(exception)

    if not outcome["written"]:
        return (
            jsonify(
                {
                    "status": "error",
                    "errors": "claim lost to another worker; result not written",
                    "data": outcome,
                }
            ),
            409,
        )
    return jsonify({"status": "success", "data": outcome})


@analysis_bp.route("/data-sources", methods=["GET"])
def list_data_sources():
    """The input-data sources this AlabOS knows about, so a client does not hardcode the lab's field names."""
    return jsonify(
        {
            "status": "success",
            "data": {
                "data_sources": [
                    {
                        "name": name,
                        "kind": source.get("kind"),
                        "field": source.get("field"),
                        "description": source.get("description"),
                    }
                    for name, source in sorted(input_data_sources().items())
                ]
            },
        }
    )
