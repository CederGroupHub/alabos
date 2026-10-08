"""Programmatic Data API under ``/api/data`` (samples, measurements, artifacts, analysis).

Dashboard report routes live in ``data_reports.py`` (same URL prefix). External clients (SEM PC, desta)
talk to these routes on alabos port 8895. See alab_one ``docs/data-api.md``.
"""

from __future__ import annotations

import contextlib
import hmac
import mimetypes
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, Response, jsonify, request, send_file

from alab_management.config import AlabOSConfig
from alab_management.dashboard.data_storage import resolve_logical_key
from alab_management.dashboard.lab_views import analysis_view, sample_view
from alab_management.sample_view.analysis_view import (
    DEFAULT_CLAIM_TTL_S,
    DEFAULT_PENDING_LIMIT,
    SampleNotFoundError,
    input_data_sources,
)
from alab_management.utils.data_objects import get_completed_collection, make_jsonable

data_api_bp = Blueprint("/data_api", __name__, url_prefix="/api/data")

TOKEN_HEADER = "X-AlabOS-Token"
TOKEN_ENV = "ALABOS_DATA_API_TOKEN"

SAMPLE_SOURCE_VALUES = frozenset({"alabos", "manual_sem", "ephemeral"})


def _configured_token() -> str | None:
    token = os.environ.get(TOKEN_ENV)
    if token:
        return token
    try:
        section = AlabOSConfig().get("data_api") or {}
    except FileNotFoundError:
        return None
    return section.get("token") or None


def _token_bytes(value: str) -> bytes:
    return value.encode("utf-8", "surrogateescape")


@data_api_bp.before_request
def _require_token():
    # Report/window routes are on a different blueprint; only programmatic paths hit this.
    expected = _configured_token()
    if expected is None:
        return None
    if hmac.compare_digest(
        _token_bytes(request.headers.get(TOKEN_HEADER, "")), _token_bytes(expected)
    ):
        return None
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


def _missing(exception: SampleNotFoundError | ValueError):
    return jsonify({"status": "error", "errors": str(exception)}), 404


def _invalid(exception: ValueError):
    return jsonify({"status": "error", "errors": str(exception)}), 400


def _sample_doc(sample_id: ObjectId) -> dict[str, Any] | None:
    return sample_view._sample_collection.find_one({"_id": sample_id})


def _find_sample_across_dbs(sample_id: ObjectId) -> tuple[dict[str, Any] | None, str]:
    doc = _sample_doc(sample_id)
    if doc is not None:
        return doc, "working"
    try:
        completed = get_completed_collection("samples")
        doc = completed.find_one({"_id": sample_id})
        if doc is not None:
            return doc, "completed"
    except ValueError:
        pass
    return None, ""


def _sample_summary(doc: dict[str, Any], db_label: str = "working") -> dict[str, Any]:
    metadata = doc.get("metadata") or {}
    source = metadata.get("source") or "alabos"
    return {
        "sample_id": str(doc["_id"]),
        "name": doc.get("name"),
        "tags": doc.get("tags") or [],
        "created_at": doc.get("created_at"),
        "last_updated": doc.get("last_updated"),
        "position": doc.get("position"),
        "database": db_label,
        "source": source,
        "metadata": {
            "source": source,
            "elements_present": metadata.get("elements_present"),
            "target": metadata.get("target"),
            "powderdosing_results": metadata.get("powderdosing_results"),
            "measurements": metadata.get("measurements") or [],
            "analysis": metadata.get("analysis") or {},
            "diffraction_results": metadata.get("diffraction_results"),
            "sem_eds_results": metadata.get("sem_eds_results"),
        },
    }


# ---- samples ----


@data_api_bp.route("/samples", methods=["GET"])
def list_samples():
    """Search samples for SEM picker / clients. Query: search, name, days, limit."""
    search = (request.args.get("search") or "").strip()
    name = (request.args.get("name") or "").strip()
    days = request.args.get("days", type=float)
    limit = request.args.get("limit", default=200, type=int) or 200
    limit = max(1, min(limit, 1000))

    query: dict[str, Any] = {}
    if name:
        query["name"] = name
    elif search:
        query["name"] = {"$regex": search, "$options": "i"}
    if days is not None and days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        # created_at may be naive local; compare loosely with naive cutoff when needed
        query["created_at"] = {"$gte": cutoff.replace(tzinfo=None)}

    projection = {
        "name": 1,
        "tags": 1,
        "created_at": 1,
        "last_updated": 1,
        "position": 1,
        "metadata.source": 1,
        "metadata.elements_present": 1,
        "metadata.target": 1,
        "metadata.measurements": 1,
    }

    samples: list[dict[str, Any]] = []
    collections: list[tuple[Any, str]] = [
        (sample_view._sample_collection, "working"),
    ]
    with contextlib.suppress(ValueError):
        collections.append((get_completed_collection("samples"), "completed"))

    seen: set[str] = set()
    for coll, label in collections:
        for doc in coll.find(query, projection).sort("created_at", -1).limit(limit):
            sid = str(doc["_id"])
            if sid in seen:
                continue
            seen.add(sid)
            samples.append(_sample_summary(doc, label))
            if len(samples) >= limit:
                break
        if len(samples) >= limit:
            break

    return jsonify(make_jsonable({"status": "success", "data": {"samples": samples}}))


@data_api_bp.route("/samples", methods=["POST"])
def create_sample():
    """Path B sample create — not wired yet (403)."""
    return (
        jsonify(
            {
                "status": "error",
                "errors": (
                    "POST /api/data/samples (Path B / manual_sem) is not implemented yet; "
                    "attach measurements to an existing alabos sample (Path A)"
                ),
            }
        ),
        403,
    )


@data_api_bp.route("/samples/<sample_id>", methods=["GET"])
def get_sample(sample_id: str):
    try:
        object_id = _sample_object_id(sample_id)
    except ValueError as exception:
        return _invalid(exception)
    doc, label = _find_sample_across_dbs(object_id)
    if doc is None:
        return jsonify({"status": "error", "errors": f"sample {sample_id} not found"}), 404
    return jsonify(
        make_jsonable({"status": "success", "data": {"sample": _sample_summary(doc, label)}})
    )


# ---- measurements ----


@data_api_bp.route("/samples/<sample_id>/measurements", methods=["GET"])
def list_measurements(sample_id: str):
    try:
        object_id = _sample_object_id(sample_id)
    except ValueError as exception:
        return _invalid(exception)
    doc, _label = _find_sample_across_dbs(object_id)
    if doc is None:
        return jsonify({"status": "error", "errors": f"sample {sample_id} not found"}), 404
    measurements = (doc.get("metadata") or {}).get("measurements") or []
    return jsonify(
        make_jsonable({"status": "success", "data": {"measurements": measurements}})
    )


@data_api_bp.route("/samples/<sample_id>/measurements", methods=["POST"])
def attach_measurement(sample_id: str):
    """Append a measurement ref on a live sample (Path A SEM / XRD registration)."""
    try:
        body = _body()
        object_id = _sample_object_id(sample_id)
        kind = body.get("kind")
        if not isinstance(kind, str) or not kind.strip():
            raise ValueError("kind must be a non-empty string")
        logical_key = body.get("logical_key")
        content_hash = body.get("content_hash")
        if not isinstance(logical_key, str) or not logical_key.strip():
            raise ValueError("logical_key must be a non-empty string")
        if content_hash is not None and not isinstance(content_hash, str):
            raise ValueError("content_hash must be a string when provided")

        measurement = {
            "kind": kind.strip(),
            "logical_key": logical_key.strip(),
            "content_hash": content_hash,
            "source": body.get("source") or "manual_sem_ingest",
            "storage": body.get("storage"),
            "created_at": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        }
        extra = body.get("extra")
        if isinstance(extra, dict):
            measurement["extra"] = extra

        if _sample_doc(object_id) is None:
            raise SampleNotFoundError(f"Cannot find sample with id: {object_id}")

        sample_view.append_measurement(object_id, measurement)
    except SampleNotFoundError as exception:
        return _missing(exception)
    except ValueError as exception:
        return _invalid(exception)

    return jsonify(
        make_jsonable({"status": "success", "data": {"measurement": measurement}})
    ), 201


# ---- artifacts ----


def _measurements_from_doc(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return list((doc.get("metadata") or {}).get("measurements") or [])


def _pick_measurement(
    measurements: list[dict[str, Any]],
    *,
    kind: str | None = None,
    logical_key: str | None = None,
    content_hash: str | None = None,
) -> dict[str, Any] | None:
    candidates = measurements
    if kind:
        candidates = [m for m in candidates if m.get("kind") == kind]
    if logical_key:
        candidates = [m for m in candidates if m.get("logical_key") == logical_key]
    if content_hash:
        candidates = [m for m in candidates if m.get("content_hash") == content_hash]
    if not candidates:
        # Fall back to diffraction_results / legacy fields when measurements[] is empty.
        return None
    return candidates[-1]


@data_api_bp.route("/samples/<sample_id>/artifacts/<kind>", methods=["GET"])
def get_artifact_by_kind(sample_id: str, kind: str):
    """Stream the raw artifact for a sample+kind by resolving ``logical_key``."""
    try:
        object_id = _sample_object_id(sample_id)
    except ValueError as exception:
        return _invalid(exception)

    doc, _label = _find_sample_across_dbs(object_id)
    if doc is None:
        return jsonify({"status": "error", "errors": f"sample {sample_id} not found"}), 404

    logical_key = request.args.get("logical_key")
    content_hash = request.args.get("content_hash")
    measurement = _pick_measurement(
        _measurements_from_doc(doc),
        kind=kind,
        logical_key=logical_key,
        content_hash=content_hash,
    )

    if measurement is None and kind in ("xrd", "xrdml", "diffraction"):
        # Legacy / technique summary field until all writers append measurements[].
        dr = (doc.get("metadata") or {}).get("diffraction_results") or {}
        logical_key = logical_key or dr.get("logical_key")
        content_hash = content_hash or dr.get("content_hash") or dr.get("xrd_raw_sha256")
        if logical_key:
            measurement = {
                "kind": kind,
                "logical_key": logical_key,
                "content_hash": content_hash,
            }

    if measurement is None or not measurement.get("logical_key"):
        return (
            jsonify(
                {
                    "status": "error",
                    "errors": f"no artifact of kind {kind!r} for sample {sample_id}",
                }
            ),
            404,
        )

    try:
        path = resolve_logical_key(measurement["logical_key"])
    except ValueError as exception:
        return _invalid(exception)

    if not path.is_file():
        return (
            jsonify(
                {
                    "status": "error",
                    "errors": f"artifact file missing on storage: {path}",
                }
            ),
            404,
        )

    mime, _ = mimetypes.guess_type(str(path))
    return send_file(
        path,
        mimetype=mime or "application/octet-stream",
        as_attachment=False,
        download_name=path.name,
    )


@data_api_bp.route("/artifacts/by-hash/<content_hash>", methods=["GET"])
def get_artifact_by_hash(content_hash: str):
    """Find a sample measurement by content_hash and stream the file."""
    if not content_hash or not content_hash.strip():
        return _invalid(ValueError("content_hash is required"))

    query = {"metadata.measurements.content_hash": content_hash}
    doc = sample_view._sample_collection.find_one(query)
    db_label = "working"
    if doc is None:
        try:
            doc = get_completed_collection("samples").find_one(query)
            db_label = "completed"
        except ValueError:
            doc = None
    if doc is None:
        # Legacy XRD field
        query_legacy = {
            "$or": [
                {"metadata.diffraction_results.content_hash": content_hash},
                {"metadata.diffraction_results.xrd_raw_sha256": content_hash},
            ]
        }
        doc = sample_view._sample_collection.find_one(query_legacy)
        if doc is None:
            try:
                doc = get_completed_collection("samples").find_one(query_legacy)
            except ValueError:
                doc = None
        if doc is None:
            return (
                jsonify(
                    {
                        "status": "error",
                        "errors": f"no measurement with content_hash {content_hash!r}",
                    }
                ),
                404,
            )

    measurement = _pick_measurement(
        _measurements_from_doc(doc), content_hash=content_hash
    )
    logical_key = None
    if measurement:
        logical_key = measurement.get("logical_key")
    if not logical_key:
        dr = (doc.get("metadata") or {}).get("diffraction_results") or {}
        logical_key = dr.get("logical_key")
    if not logical_key:
        return jsonify({"status": "error", "errors": "measurement has no logical_key"}), 404

    try:
        path = resolve_logical_key(logical_key)
    except ValueError as exception:
        return _invalid(exception)
    if not path.is_file():
        return jsonify({"status": "error", "errors": f"artifact file missing: {path}"}), 404

    mime, _ = mimetypes.guess_type(str(path))
    response = send_file(
        path,
        mimetype=mime or "application/octet-stream",
        as_attachment=False,
        download_name=path.name,
    )
    if isinstance(response, Response):
        response.headers["X-AlabOS-Sample-Id"] = str(doc["_id"])
        response.headers["X-AlabOS-Database"] = db_label
    return response


# ---- analysis (from #105, under /api/data/analysis) ----


@data_api_bp.route("/analysis/pending", methods=["GET"])
def list_pending():
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


@data_api_bp.route("/analysis/claim/<sample_id>", methods=["POST"])
def claim_sample(sample_id: str):
    held = None
    claim = None
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


@data_api_bp.route("/analysis/claim/<sample_id>/release", methods=["POST"])
def release_sample(sample_id: str):
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


@data_api_bp.route("/analysis/results/<sample_id>", methods=["POST"])
def write_result(sample_id: str):
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


@data_api_bp.route("/analysis/data-sources", methods=["GET"])
def list_data_sources():
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
