"""Background jobs for Submissions free-form (single-device) drafts."""

from __future__ import annotations

import json
import os
import re
import threading
import uuid
from datetime import datetime
from typing import Any

DRAFT_JSON_RE = re.compile(r"DRAFT_JSON=(\{.*\})\s*$", re.DOTALL | re.MULTILINE)
LOG_TAIL_MAX = 50_000
DEFAULT_MODEL = "composer-2.5"

_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}
_current_job_id: str | None = None
_active_thread: threading.Thread | None = None

PROMPT_PREAMBLE = """You are proposing a single-device ALab experiment draft.

Hard limits:
- Exactly ONE device and ONE task type (Heating on a box furnace for V1).
- Do NOT invent multi-device chains (PowderDosing, Moving between stations, Diffraction,
  RecoverPowder, Ending). Those belong on the Recipes tab.
- You MUST use the provided sample_id / sample_name. Do not invent other samples.

Return exactly one line at the end (and nothing after it):
DRAFT_JSON={{"heating_temperature_c": <number>, "heating_duration_minutes": <number>,
"ramping_rate_c_per_min": <number>, "cooling_rate_c_per_min": null or number}}

Context:
- device_name: {device_name}
- sample_id: {sample_id}
- sample_name: {sample_name}
- physical_placement: {physical_placement}

---
Operator request:
"""


class SubmissionAgentError(Exception):
    """Expected job start failures."""

    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def _freeform():
    """The lab-specific free-form module, imported on use so AlabOS starts without `alab_one`."""
    try:
        from alab_one.submissions import freeform
    except ImportError as exception:
        raise SubmissionAgentError(
            "Free-form submissions need the lab-specific 'alab_one' package, "
            f"which is not available here ({exception}).",
            status_code=503,
        ) from exception
    return freeform


def _now() -> datetime:
    return datetime.now()


def _job_public(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": job["id"],
        "status": job["status"],
        "prompt": job["prompt"],
        "device_name": job.get("device_name"),
        "sample_id": job.get("sample_id"),
        "created_at": job["created_at"].isoformat(timespec="seconds")
        if isinstance(job.get("created_at"), datetime)
        else job.get("created_at"),
        "updated_at": job["updated_at"].isoformat(timespec="seconds")
        if isinstance(job.get("updated_at"), datetime)
        else job.get("updated_at"),
        "log_tail": (job.get("log_tail") or "")[-LOG_TAIL_MAX:],
        "error": job.get("error"),
        "draft": job.get("draft"),
        "agent_id": job.get("agent_id"),
    }


def parse_draft_json(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    match = DRAFT_JSON_RE.search(text)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def build_agent_prompt(
    user_prompt: str,
    *,
    device_name: str,
    sample_id: str,
    sample_name: str,
    physical_placement: Any = None,
) -> str:
    return PROMPT_PREAMBLE.format(
        device_name=device_name,
        sample_id=sample_id,
        sample_name=sample_name,
        physical_placement=json.dumps(physical_placement),
    ) + str(user_prompt or "").strip()


def _append_log(job_id: str, chunk: str) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        job["log_tail"] = ((job.get("log_tail") or "") + chunk)[-LOG_TAIL_MAX:]
        job["updated_at"] = _now()


def _set_job(job_id: str, **fields: Any) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        job.update(fields)
        job["updated_at"] = _now()


def _build_draft_from_params(
    *,
    prompt: str,
    device_name: str,
    sample_id: str,
    sample_name: str,
    reuse_existing: bool,
    physical_placement: dict[str, Any] | None,
    params: dict[str, Any],
) -> dict[str, Any]:
    experiment = _freeform().build_heating_experiment(
        sample_name=sample_name,
        sample_id=sample_id,
        device_name=device_name,
        heating_temperature_c=float(params["heating_temperature_c"]),
        heating_duration_minutes=float(params["heating_duration_minutes"]),
        ramping_rate_c_per_min=float(params.get("ramping_rate_c_per_min") or 5),
        cooling_rate_c_per_min=params.get("cooling_rate_c_per_min"),
        profiles=params.get("profiles"),
        reuse_existing=reuse_existing,
        prompt=prompt,
        physical_placement=physical_placement,
    )
    return {
        "params": params,
        "experiment": experiment,
        "device_name": device_name,
        "sample_id": sample_id,
        "sample_name": sample_name,
    }


def _try_cursor_refine(
    job_id: str,
    *,
    prompt: str,
    device_name: str,
    sample_id: str,
    sample_name: str,
    physical_placement: Any,
) -> dict[str, Any] | None:
    """Optional Cursor SDK refinement; returns heating params or None."""
    api_key = (os.environ.get("CURSOR_API_KEY") or "").strip()
    if not api_key:
        _append_log(job_id, "No CURSOR_API_KEY; using local parser.\n")
        return None
    try:
        from cursor_sdk import AsyncAgent, AsyncClient  # type: ignore
    except ImportError:
        _append_log(job_id, "cursor-sdk not installed; using local parser.\n")
        return None

    agent_prompt = build_agent_prompt(
        prompt,
        device_name=device_name,
        sample_id=sample_id,
        sample_name=sample_name,
        physical_placement=physical_placement,
    )

    async def _run() -> str:
        client = AsyncClient(api_key=api_key)
        model = (os.environ.get("CURSOR_SUBMISSION_MODEL") or DEFAULT_MODEL).strip()
        agent = await AsyncAgent.create(client, model=model)
        _set_job(job_id, agent_id=getattr(agent, "id", None))
        run = await agent.send(agent_prompt)
        text_parts: list[str] = []
        async for event in run.stream():
            piece = getattr(event, "text", None) or getattr(event, "delta", None) or ""
            if piece:
                text_parts.append(str(piece))
                _append_log(job_id, str(piece))
        await run.wait()
        return "".join(text_parts)

    import asyncio

    try:
        text = asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        _append_log(job_id, f"\nCursor refine failed: {exc}\n")
        return None
    return parse_draft_json(text)


def _run_job(job_id: str, payload: dict[str, Any]) -> None:
    try:
        _set_job(job_id, status="running")
        prompt = payload["prompt"]
        device_name = payload["device_name"]
        sample_id = payload["sample_id"]
        sample_name = payload["sample_name"]
        reuse_existing = bool(payload.get("reuse_existing"))
        physical_placement = payload.get("physical_placement")

        refusal = _freeform().reject_if_multi_device(prompt)
        if refusal:
            _set_job(job_id, status="failed", error=refusal)
            return
        if device_name not in _freeform().DEVICE_BY_NAME:
            _set_job(
                job_id,
                status="failed",
                error=f"Device {device_name} is not allowlisted for free-form.",
            )
            return

        params = _freeform().parse_heating_params_from_prompt(prompt)
        refined = _try_cursor_refine(
            job_id,
            prompt=prompt,
            device_name=device_name,
            sample_id=sample_id,
            sample_name=sample_name,
            physical_placement=physical_placement,
        )
        if refined:
            params.update({k: v for k, v in refined.items() if v is not None})
            _append_log(job_id, f"\nUsing refined params: {params}\n")
        else:
            _append_log(job_id, f"\nUsing parsed params: {params}\n")

        draft = _build_draft_from_params(
            prompt=prompt,
            device_name=device_name,
            sample_id=sample_id,
            sample_name=sample_name,
            reuse_existing=reuse_existing,
            physical_placement=physical_placement,
            params=params,
        )
        _set_job(job_id, status="succeeded", draft=draft, error=None)
    except Exception as exc:  # noqa: BLE001
        _set_job(job_id, status="failed", error=str(exc))


def start_freeform_job(payload: dict[str, Any]) -> dict[str, Any]:
    prompt = str(payload.get("prompt") or "").strip()
    if not prompt:
        raise SubmissionAgentError("prompt is required")
    device_name = str(payload.get("device_name") or "").strip()
    if not device_name:
        raise SubmissionAgentError("device_name is required")
    sample_id = str(payload.get("sample_id") or "").strip()
    sample_name = str(payload.get("sample_name") or "").strip()
    if not sample_id or not sample_name:
        raise SubmissionAgentError("sample_id and sample_name are required")

    refusal = _freeform().reject_if_multi_device(prompt)
    if refusal:
        raise SubmissionAgentError(refusal)

    global _current_job_id, _active_thread
    with _lock:
        if _active_thread is not None and _active_thread.is_alive():
            raise SubmissionAgentError(
                "A free-form submission job is already running. Wait for it to finish.",
                status_code=409,
            )
        job_id = uuid.uuid4().hex
        now = _now()
        job = {
            "id": job_id,
            "status": "queued",
            "prompt": prompt,
            "device_name": device_name,
            "sample_id": sample_id,
            "sample_name": sample_name,
            "created_at": now,
            "updated_at": now,
            "log_tail": "",
            "error": None,
            "draft": None,
            "agent_id": None,
        }
        _jobs[job_id] = job
        _current_job_id = job_id
        body = {
            "prompt": prompt,
            "device_name": device_name,
            "sample_id": sample_id,
            "sample_name": sample_name,
            "reuse_existing": bool(payload.get("reuse_existing", True)),
            "physical_placement": payload.get("physical_placement"),
        }
        thread = threading.Thread(
            target=_run_job,
            args=(job_id, body),
            name=f"submission-agent-{job_id[:8]}",
            daemon=True,
        )
        _active_thread = thread
        thread.start()
        return _job_public(job)


def get_job(job_id: str) -> dict[str, Any] | None:
    with _lock:
        job = _jobs.get(job_id)
        return _job_public(job) if job else None


def get_current_job() -> dict[str, Any] | None:
    with _lock:
        if not _current_job_id:
            return None
        job = _jobs.get(_current_job_id)
        return _job_public(job) if job else None


def reset_jobs_for_tests() -> None:
    global _current_job_id, _active_thread
    with _lock:
        _jobs.clear()
        _current_job_id = None
        _active_thread = None
