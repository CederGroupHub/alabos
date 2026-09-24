"""Background Cursor SDK jobs that author Data report generators."""

from __future__ import annotations

import os
import re
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

REPORT_NAME_RE = re.compile(r"^REPORT_NAME=([a-z][a-z0-9_]*)\s*$", re.MULTILINE)
LOG_TAIL_MAX = 50_000
DEFAULT_MODEL = "composer-2.5"
DEFAULT_DASHBOARD_BASE = "http://127.0.0.1:8895"

_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}
_current_job_id: str | None = None
_active_thread: threading.Thread | None = None

PROMPT_PREAMBLE = """You are authoring a reusable ALab Data page report.

Follow docs/data-reports-cursor.md and .cursor/skills/alab-data-report/SKILL.md.

Deliverable (mandatory — do not stop at a chat table):
1. Create or update `alab_management/dashboard/user_reports/<slug>.py` with:
   `def run(*, start, end, live_db, completed_db) -> dict` returning
   `{{"columns": [{{"key","label"}}, ...], "rows": [...]}}` (max 5000 rows).
2. Use read-only queries only. Prefer `alab_management.dashboard.report_db.find_union`
   when names may live in both Alab and Alab(completed). Never write samples/tasks/experiments.
3. Register the report via HTTP POST to `{dashboard_base}/api/data/reports` with JSON:
   {{
     "name": "<slug>",
     "title": "<human title>",
     "description": "<short description>",
     "enabled": true,
     "saved": true,
     "generator": {{"type": "module", "module": "<slug>"}},
     "prompt": "<original user request>",
     "created_by": "data_page_agent"
   }}
   The module file must exist on disk before that POST (the API imports it).
4. Reuse patterns from builtins: sample_report.py, sample_summary.py,
   powder_dosing_actuals.py, task_outcome_log.py.
5. Do not git commit. Do not modify builtins. Do not invent write APIs for lab data.

Slug rules: lowercase snake_case, letters/digits/underscore, must start with a letter.

When finished, print exactly one line (no other trailing text after it):
REPORT_NAME=<slug>

---
Operator request:
"""


class ReportAgentError(Exception):
    """Raised for expected job start failures (missing key, busy, bad input)."""

    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def _now() -> datetime:
    return datetime.now()


def repo_root() -> Path:
    override = (os.environ.get("ALAB_MANAGEMENT_ROOT") or "").strip()
    if override:
        return Path(override).resolve()
    # alab_management/dashboard/report_agent.py → repo root is parents[2]
    return Path(__file__).resolve().parents[2]


def dashboard_base_url() -> str:
    return (os.environ.get("ALAB_DASHBOARD_BASE") or DEFAULT_DASHBOARD_BASE).rstrip("/")


def api_key() -> str | None:
    key = (os.environ.get("CURSOR_API_KEY") or "").strip()
    return key or None


def model_id() -> str:
    return (os.environ.get("CURSOR_DATA_REPORT_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL


def build_agent_prompt(user_prompt: str, *, dashboard_base: str | None = None) -> str:
    text = str(user_prompt or "").strip()
    base = dashboard_base or dashboard_base_url()
    return PROMPT_PREAMBLE.format(dashboard_base=base) + text


def parse_report_name(text: str) -> str | None:
    if not text:
        return None
    matches = REPORT_NAME_RE.findall(text)
    if not matches:
        return None
    return matches[-1]


def _job_public(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": job["id"],
        "status": job["status"],
        "prompt": job["prompt"],
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
        "log_tail": job.get("log_tail") or "",
        "error": job.get("error"),
        "report_name": job.get("report_name"),
        "agent_id": job.get("agent_id"),
    }


def get_job(job_id: str) -> dict[str, Any] | None:
    with _lock:
        job = _jobs.get(job_id)
        return _job_public(job) if job else None


def get_current_job() -> dict[str, Any] | None:
    with _lock:
        if _current_job_id and _current_job_id in _jobs:
            return _job_public(_jobs[_current_job_id])
        if not _jobs:
            return None
        latest = max(_jobs.values(), key=lambda j: j["created_at"])
        return _job_public(latest)


def is_busy() -> bool:
    with _lock:
        if _active_thread is not None and _active_thread.is_alive():
            return True
        if _current_job_id:
            job = _jobs.get(_current_job_id)
            if job and job["status"] in ("queued", "running"):
                return True
        return False


def _append_log(job_id: str, chunk: str) -> None:
    if not chunk:
        return
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        text = (job.get("log_tail") or "") + chunk
        if len(text) > LOG_TAIL_MAX:
            text = text[-LOG_TAIL_MAX:]
        job["log_tail"] = text
        job["updated_at"] = _now()


def _set_job_fields(job_id: str, **fields: Any) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        job.update(fields)
        job["updated_at"] = _now()


def _catalog_names() -> set[str]:
    from alab_management.dashboard import data_reports as reports

    try:
        reports.ensure_builtin_reports()
        items = reports.list_reports(enabled_only=False)
    except Exception:
        return set()
    return {str(item.get("name")) for item in items if item.get("name")}


def _extract_stream_text(message: Any) -> str:
    parts: list[str] = []
    msg_type = getattr(message, "type", None)
    payload = getattr(message, "message", None)
    content = getattr(payload, "content", None) if payload is not None else None
    if content is None and isinstance(message, dict):
        content = (message.get("message") or {}).get("content")
        msg_type = message.get("type")
    # Capture assistant text only for the log (keep noise down).
    if msg_type != "assistant":
        return ""
    if not content:
        return ""
    for block in content:
        block_type = getattr(block, "type", None) or (
            block.get("type") if isinstance(block, dict) else None
        )
        if block_type == "text":
            text = getattr(block, "text", None)
            if text is None and isinstance(block, dict):
                text = block.get("text")
            if text:
                parts.append(str(text))
    return "".join(parts)


def _run_sdk_job(job_id: str, user_prompt: str, names_before: set[str]) -> None:
    _set_job_fields(job_id, status="running")
    full_prompt = build_agent_prompt(user_prompt)
    _append_log(job_id, "Starting Cursor local agent…\n")

    try:
        try:
            from cursor_sdk import Agent, LocalAgentOptions
        except ImportError as exc:
            raise RuntimeError(
                "cursor-sdk is not installed. "
                'Install with: pip install "alab_management[data_reports]" '
                "or pip install cursor-sdk"
            ) from exc

        key = api_key()
        if not key:
            raise RuntimeError("CURSOR_API_KEY is not set on the dashboard process.")

        cwd = str(repo_root())
        _append_log(job_id, f"cwd={cwd}\nmodel={model_id()}\n")

        final_text = ""
        with Agent.create(
            model=model_id(),
            api_key=key,
            local=LocalAgentOptions(cwd=cwd),
        ) as agent:
            agent_id = getattr(agent, "agent_id", None) or getattr(agent, "id", None)
            if agent_id:
                _set_job_fields(job_id, agent_id=str(agent_id))
            run = agent.send(full_prompt)
            try:
                for message in run.messages():
                    chunk = _extract_stream_text(message)
                    if chunk:
                        final_text += chunk
                        _append_log(job_id, chunk)
            except Exception:
                # Streaming optional; still wait for terminal result.
                pass
            result = run.wait()
            status = getattr(result, "status", None)
            result_text = getattr(result, "result", None)
            if isinstance(result_text, str) and result_text:
                final_text = final_text + ("\n" if final_text else "") + result_text
                _append_log(job_id, "\n" + result_text)
            if status == "error":
                run_id = getattr(result, "id", "unknown")
                raise RuntimeError(f"Cursor agent run failed (id={run_id}).")

        report_name = parse_report_name(final_text)
        if not report_name:
            names_after = _catalog_names()
            new_names = sorted(names_after - names_before)
            if new_names:
                report_name = new_names[0]
        if not report_name:
            raise RuntimeError(
                "Agent finished but no REPORT_NAME= line and no new registry entry found."
            )

        _set_job_fields(
            job_id,
            status="succeeded",
            report_name=report_name,
            error=None,
        )
        _append_log(job_id, f"\nDone. REPORT_NAME={report_name}\n")
    except Exception as exc:
        # CursorAgentError and everything else → failed job
        message = getattr(exc, "message", None) or str(exc)
        _set_job_fields(job_id, status="failed", error=message)
        _append_log(job_id, f"\nERROR: {message}\n")
    finally:
        global _active_thread
        with _lock:
            _active_thread = None
            # Keep _current_job_id pointing at this finished job for /current.


def start_report_job(user_prompt: str) -> dict[str, Any]:
    """Queue a one-shot Cursor agent job. Raises ReportAgentError on reject."""
    text = str(user_prompt or "").strip()
    if not text:
        raise ReportAgentError("prompt is required.", status_code=400)
    if not api_key():
        raise ReportAgentError(
            "CURSOR_API_KEY is not set on the dashboard server. "
            "Set it in the process environment and restart.",
            status_code=503,
        )
    try:
        import cursor_sdk  # noqa: F401
    except ImportError as exc:
        raise ReportAgentError(
            'cursor-sdk is not installed. '
            'Install with: pip install "alab_management[data_reports]" '
            "or pip install cursor-sdk",
            status_code=503,
        ) from exc

    global _current_job_id, _active_thread
    with _lock:
        if _active_thread is not None and _active_thread.is_alive():
            raise ReportAgentError(
                "A report agent job is already running. Wait for it to finish.",
                status_code=409,
            )
        if _current_job_id:
            existing = _jobs.get(_current_job_id)
            if existing and existing["status"] in ("queued", "running"):
                raise ReportAgentError(
                    "A report agent job is already running. Wait for it to finish.",
                    status_code=409,
                )

        job_id = uuid.uuid4().hex
        now = _now()
        job = {
            "id": job_id,
            "status": "queued",
            "prompt": text,
            "created_at": now,
            "updated_at": now,
            "log_tail": "",
            "error": None,
            "report_name": None,
            "agent_id": None,
        }
        _jobs[job_id] = job
        _current_job_id = job_id
        names_before = _catalog_names()
        thread = threading.Thread(
            target=_run_sdk_job,
            args=(job_id, text, names_before),
            name=f"report-agent-{job_id[:8]}",
            daemon=True,
        )
        _active_thread = thread
        thread.start()
        return _job_public(job)


def reset_jobs_for_tests() -> None:
    """Clear in-memory job state (unit tests only)."""
    global _current_job_id, _active_thread
    with _lock:
        _jobs.clear()
        _current_job_id = None
        _active_thread = None
