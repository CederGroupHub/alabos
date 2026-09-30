"""Submissions API: guided recipes + single-device free-form."""

from __future__ import annotations

import logging
from typing import Any

from bson import ObjectId  # type: ignore
from bson.errors import InvalidId  # type: ignore
from flask import Blueprint, request
from pydantic import ValidationError

from alab_management.dashboard import submission_agent
from alab_management.dashboard.lab_views import experiment_view, sample_view
from alab_management.experiment_view.experiment import InputExperiment
from alab_management.utils.data_objects import make_jsonable

logger = logging.getLogger(__name__)

submissions_bp = Blueprint("/submissions", __name__, url_prefix="/api/submissions")


def _submit_experiment_dict(experiment: dict[str, Any]) -> tuple[dict[str, Any], int]:
    from alab_management.device_rpc_status import (
        ensure_lab_starting_user_input,
        get_lab_readiness,
    )

    try:
        parsed = InputExperiment(**experiment)
        exp_id = experiment_view.create_experiment(parsed)
    except ValidationError as exception:
        return {"status": "error", "errors": exception.errors()}, 400
    except ValueError as exception:
        return {"status": "error", "errors": exception.args[0]}, 400

    readiness = get_lab_readiness()
    held = not readiness["lab_ready"]
    if held:
        ensure_lab_starting_user_input()

    return {
        "status": "success",
        "data": {
            "exp_id": str(exp_id),
            "lab_ready": readiness["lab_ready"],
            "lab_ready_label": readiness["lab_ready_label"],
            "held_until_lab_ready": held,
        },
    }, 200


@submissions_bp.route("/recipes", methods=["GET"])
def list_recipes():
    from alab_one.submissions.recipes import get_recipe_catalog

    return {"status": "success", "recipes": get_recipe_catalog()}


@submissions_bp.route("/recipes/<recipe_id>/preview", methods=["POST"])
def preview_recipe(recipe_id: str):
    from alab_one.submissions.recipes import build_recipe, preview_from_batch

    payload = request.get_json(force=True) or {}
    try:
        batch = build_recipe(recipe_id, payload)
        return preview_from_batch(batch)
    except TypeError as exc:
        return {"status": "error", "errors": str(exc)}, 400
    except ValueError as exc:
        return {"status": "error", "errors": str(exc)}, 400
    except Exception as exc:  # noqa: BLE001
        logger.exception("recipe preview failed")
        return {"status": "error", "errors": str(exc)}, 400


@submissions_bp.route("/recipes/<recipe_id>/submit", methods=["POST"])
def submit_recipe(recipe_id: str):
    from alab_one.submissions.recipes import build_recipe, experiment_payload_from_batch

    payload = request.get_json(force=True) or {}
    try:
        batch = build_recipe(recipe_id, payload)
        experiment = experiment_payload_from_batch(batch)
        experiment["metadata"] = {
            **(experiment.get("metadata") or {}),
            "recipe_id": recipe_id,
        }
        body, status = _submit_experiment_dict(experiment)
        return body, status
    except TypeError as exc:
        return {"status": "error", "errors": str(exc)}, 400
    except ValueError as exc:
        return {"status": "error", "errors": str(exc)}, 400
    except Exception as exc:  # noqa: BLE001
        logger.exception("recipe submit failed")
        return {"status": "error", "errors": str(exc)}, 400


@submissions_bp.route("/freeform/devices", methods=["GET"])
def freeform_devices():
    from alab_one.submissions.freeform import get_freeform_devices

    return {"status": "success", "devices": get_freeform_devices()}


@submissions_bp.route("/samples/resolve", methods=["POST"])
def resolve_samples():
    payload = request.get_json(force=True) or {}
    query = str(payload.get("query") or payload.get("q") or "").strip()
    limit = min(int(payload.get("limit") or 25), 100)
    if not query:
        return {"status": "success", "samples": []}

    samples: list[dict[str, Any]] = []
    # Exact ObjectId match
    try:
        oid = ObjectId(query)
        doc = sample_view._sample_collection.find_one({"_id": oid})
        if doc:
            samples.append(
                {
                    "sample_id": str(doc["_id"]),
                    "name": doc.get("name"),
                    "position": doc.get("position"),
                    "tags": doc.get("tags") or [],
                    "metadata": doc.get("metadata") or {},
                }
            )
            return {"status": "success", "samples": make_jsonable(samples)}
    except (InvalidId, TypeError):
        pass

    cursor = (
        sample_view._sample_collection.find(
            {"name": {"$regex": query, "$options": "i"}}
        )
        .sort("name", 1)
        .limit(limit)
    )
    for doc in cursor:
        samples.append(
            {
                "sample_id": str(doc["_id"]),
                "name": doc.get("name"),
                "position": doc.get("position"),
                "tags": doc.get("tags") or [],
                "metadata": doc.get("metadata") or {},
            }
        )
    return {"status": "success", "samples": make_jsonable(samples)}


@submissions_bp.route("/samples/create", methods=["POST"])
def create_sample():
    payload = request.get_json(force=True) or {}
    name = str(payload.get("name") or "").strip()
    if not name:
        return {"status": "error", "errors": "name is required"}, 400
    position = payload.get("position")
    if position is not None:
        position = str(position).strip() or None
    tags = payload.get("tags") or []
    metadata = payload.get("metadata") or {}
    try:
        sample_id = sample_view.create_sample(
            name=name,
            position=position,
            tags=list(tags),
            metadata=dict(metadata),
        )
    except ValueError as exc:
        return {"status": "error", "errors": str(exc)}, 400
    return {
        "status": "success",
        "sample_id": str(sample_id),
        "name": name,
        "position": position,
    }


@submissions_bp.route("/freeform/jobs", methods=["POST"])
def create_freeform_job():
    payload = request.get_json(force=True) or {}
    try:
        job = submission_agent.start_freeform_job(payload)
    except submission_agent.SubmissionAgentError as exc:
        return {"status": "error", "errors": str(exc)}, exc.status_code
    return {"status": "success", **job}


@submissions_bp.route("/freeform/jobs/current", methods=["GET"])
def current_freeform_job():
    job = submission_agent.get_current_job()
    if not job:
        return {"status": "success", "job": None}
    return {"status": "success", "job": job}


@submissions_bp.route("/freeform/jobs/<job_id>", methods=["GET"])
def get_freeform_job(job_id: str):
    job = submission_agent.get_job(job_id)
    if not job:
        return {"status": "error", "errors": "job not found"}, 404
    return job


@submissions_bp.route("/freeform/confirm", methods=["POST"])
def confirm_freeform():
    payload = request.get_json(force=True) or {}
    experiment = payload.get("experiment")
    if not isinstance(experiment, dict):
        return {"status": "error", "errors": "experiment is required"}, 400
    # Enforce single-task Heating
    tasks = experiment.get("tasks") or []
    if len(tasks) != 1 or tasks[0].get("type") != "Heating":
        return {
            "status": "error",
            "errors": (
                "Free-form confirm only accepts a single Heating task. "
                "Use Recipes for multi-device flows."
            ),
        }, 400
    meta = dict(experiment.get("metadata") or {})
    meta.setdefault("submitted_via", "submissions_freeform")
    experiment["metadata"] = meta
    body, status = _submit_experiment_dict(experiment)
    return body, status
