"""Data report registry, allowlisted module runner, and snapshot cache."""

from __future__ import annotations

import importlib
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from datetime import datetime
from types import ModuleType
from typing import Any

from alab_management.dashboard.readonly_db import ReadOnlyDatabase, ReadOnlyError
from alab_management.utils.data_objects import (
    get_collection,
    get_completed_db,
    get_db,
    make_jsonable,
)

REPORTS_COLLECTION = "data_reports"
USER_REPORTS_PACKAGE = "alab_management.dashboard.user_reports"
MAX_REPORT_ROWS = 5000
MAX_CELL_CHARS = 8000
REFRESH_TIMEOUT_SECONDS = 120
MODULE_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")

BUILTIN_REPORTS: list[dict[str, Any]] = [
    {
        "name": "sample_report",
        "title": "Sample dosing & related tasks",
        "description": (
            "One row per sample name with Labman dosing (target and actual "
            "masses in separate columns), crucible/"
            "mixing pot, heating, and related task statuses. Trailing numeric "
            "copies (Sample_66_1) are folded into Sample_66."
        ),
        "generator": {"type": "module", "module": "sample_report"},
        "row_detail": "sample_report",
    },
    {
        "name": "sample_summary",
        "title": "Sample Summary",
        "description": "Samples created during the selected date range.",
        "generator": {"type": "module", "module": "sample_summary"},
        "row_detail": None,
    },
    {
        "name": "powder_dosing_actuals",
        "title": "Powder Dosing Actuals",
        "description": "Flattened per-sample Labman dosing results for the selected date range.",
        "generator": {"type": "module", "module": "powder_dosing_actuals"},
        "row_detail": None,
    },
    {
        "name": "task_outcome_log",
        "title": "Task Outcome Log",
        "description": "Task status and result-key overview for the selected date range.",
        "generator": {"type": "module", "module": "task_outcome_log"},
        "row_detail": None,
    },
]


def reports_collection():
    return get_collection(REPORTS_COLLECTION)


def _now() -> datetime:
    return datetime.now()


def validate_module_name(module_name: str) -> str:
    name = str(module_name or "").strip()
    if not MODULE_NAME_RE.match(name):
        raise ValueError(
            "generator.module must be a lowercase snake_case identifier "
            "(letters, digits, underscore)."
        )
    if name.startswith("_"):
        raise ValueError("generator.module cannot start with underscore.")
    return name


def load_user_report_module(module_name: str, *, force_reload: bool = True) -> ModuleType:
    """Import ``alab_management.dashboard.user_reports.<module_name>`` only.

    By default, drop the cached module (and shared report helpers) from
    ``sys.modules`` and re-import from disk so Data → Refresh picks up
    generator edits without restarting AlabOS.
    """
    safe = validate_module_name(module_name)
    full_name = f"{USER_REPORTS_PACKAGE}.{safe}"
    if force_reload:
        # Evict the generator and helpers it commonly binds at import time.
        for name in (
            full_name,
            "alab_management.dashboard.sample_report",
            "alab_management.dashboard.report_db",
        ):
            sys.modules.pop(name, None)
    module = importlib.import_module(full_name)
    if not module.__name__.startswith(USER_REPORTS_PACKAGE + "."):
        raise ValueError(f"Refusing to load module outside {USER_REPORTS_PACKAGE}.")
    if not hasattr(module, "run") or not callable(module.run):
        raise ValueError(f"Module '{safe}' must define a callable run(...).")
    return module


def _read_only_handles() -> tuple[ReadOnlyDatabase, ReadOnlyDatabase | None]:
    live = ReadOnlyDatabase(get_db())
    try:
        completed = ReadOnlyDatabase(get_completed_db())
    except ValueError:
        completed = None
    return live, completed


def _normalize_columns(columns: Any) -> list[dict[str, str]]:
    if not isinstance(columns, list) or not columns:
        raise ValueError("Report must return a non-empty columns list.")
    normalized: list[dict[str, str]] = []
    for entry in columns:
        if not isinstance(entry, dict):
            raise ValueError("Each column must be an object with key and label.")
        key = str(entry.get("key") or "").strip()
        if not key:
            raise ValueError("Column key is required.")
        label = str(entry.get("label") or key)
        normalized.append({"key": key, "label": label})
    return normalized


def _normalize_rows(rows: Any, columns: list[dict[str, str]]) -> list[dict[str, Any]]:
    if rows is None:
        rows = []
    if not isinstance(rows, list):
        raise ValueError("Report rows must be a list.")
    if len(rows) > MAX_REPORT_ROWS:
        raise ValueError(f"Report exceeds max rows ({MAX_REPORT_ROWS}).")
    keys = [col["key"] for col in columns]
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Each row must be an object.")
        out: dict[str, Any] = {}
        for key in keys:
            value = row.get(key)
            if isinstance(value, str) and len(value) > MAX_CELL_CHARS:
                value = value[:MAX_CELL_CHARS] + "…"
            out[key] = value
        # Preserve nested detail payloads used by sample dosing expand UI.
        for extra in ("powders", "related_tasks", "sample_ids", "aliases"):
            if extra in row and extra not in out:
                out[extra] = row[extra]
        normalized.append(out)
    return normalized


def normalize_report_result(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise ValueError("run() must return a dict with columns and rows.")
    columns = _normalize_columns(result.get("columns"))
    rows = _normalize_rows(result.get("rows"), columns)
    return {"columns": columns, "rows": make_jsonable(rows)}


def run_generator_module(
    module_name: str,
    *,
    start: datetime,
    end: datetime,
    timeout_seconds: float = REFRESH_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Load an allowlisted user_reports module and call run() under a timeout."""
    module = load_user_report_module(module_name)
    live, completed = _read_only_handles()

    result_box: dict[str, Any] = {}
    error_box: dict[str, BaseException] = {}

    def _call() -> None:
        try:
            raw = module.run(
                start=start,
                end=end,
                live_db=live,
                completed_db=completed,
            )
            result_box["result"] = normalize_report_result(raw)
        except BaseException as exc:  # noqa: BLE001 — surface to caller
            error_box["error"] = exc

    # Thread timeout avoids hanging the dashboard on a stuck generator.
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_call)
        try:
            future.result(timeout=timeout_seconds)
        except FuturesTimeout as exc:
            raise TimeoutError(
                f"Report generator '{module_name}' timed out after {timeout_seconds}s."
            ) from exc

    if "error" in error_box:
        raise error_box["error"]
    return result_box["result"]


def catalog_projection() -> dict[str, int]:
    return {
        "name": 1,
        "title": 1,
        "description": 1,
        "enabled": 1,
        "saved": 1,
        "builtin": 1,
        "generator": 1,
        "row_detail": 1,
        "prompt": 1,
        "window": 1,
        "updated_at": 1,
        "created_at": 1,
        "created_by": 1,
        # omit rows
    }


def list_reports(*, enabled_only: bool = True) -> list[dict[str, Any]]:
    query: dict[str, Any] = {}
    if enabled_only:
        query["enabled"] = {"$ne": False}
    cursor = reports_collection().find(query, catalog_projection()).sort("title", 1)
    return [make_jsonable(doc) for doc in cursor]


def get_report(name: str) -> dict[str, Any] | None:
    doc = reports_collection().find_one({"name": name})
    return make_jsonable(doc) if doc else None


def get_report_snapshot(name: str) -> dict[str, Any] | None:
    doc = reports_collection().find_one(
        {"name": name},
        {
            "name": 1,
            "title": 1,
            "description": 1,
            "columns": 1,
            "rows": 1,
            "window": 1,
            "row_detail": 1,
            "updated_at": 1,
            "builtin": 1,
            "saved": 1,
            "generator": 1,
        },
    )
    return make_jsonable(doc) if doc else None


def ensure_builtin_reports() -> None:
    """Idempotently insert/update the four builtin registry entries."""
    coll = reports_collection()
    now = _now()
    for entry in BUILTIN_REPORTS:
        existing = coll.find_one({"name": entry["name"]})
        if existing:
            coll.update_one(
                {"name": entry["name"]},
                {
                    "$set": {
                        "title": entry["title"],
                        "description": entry["description"],
                        "generator": entry["generator"],
                        "row_detail": entry.get("row_detail"),
                        "enabled": True,
                        "saved": True,
                        "builtin": True,
                        "updated_at": now,
                    }
                },
            )
            continue
        coll.insert_one(
            {
                **entry,
                "enabled": True,
                "saved": True,
                "builtin": True,
                "columns": [],
                "rows": [],
                "window": None,
                "prompt": None,
                "created_at": now,
                "updated_at": now,
                "created_by": "system",
            }
        )


def upsert_report_metadata(payload: dict[str, Any], *, created_by: str = "cursor") -> dict[str, Any]:
    """Create or update registry metadata (does not run the generator)."""
    name = str(payload.get("name") or "").strip()
    if not MODULE_NAME_RE.match(name):
        raise ValueError("name must be a lowercase snake_case slug.")
    generator = payload.get("generator") or {}
    if not isinstance(generator, dict) or generator.get("type") != "module":
        raise ValueError("generator.type must be 'module'.")
    module_name = validate_module_name(str(generator.get("module") or name))
    # Ensure module exists at register time.
    load_user_report_module(module_name)

    coll = reports_collection()
    existing = coll.find_one({"name": name})
    if existing and existing.get("builtin"):
        raise ValueError(f"Cannot overwrite builtin report '{name}'.")

    now = _now()
    doc = {
        "name": name,
        "title": str(payload.get("title") or name),
        "description": str(payload.get("description") or ""),
        "enabled": bool(payload.get("enabled", True)),
        "saved": bool(payload.get("saved", False)),
        "builtin": False,
        "generator": {"type": "module", "module": module_name},
        "row_detail": payload.get("row_detail"),
        "prompt": payload.get("prompt"),
        "updated_at": now,
        "created_by": created_by,
    }
    if existing:
        coll.update_one({"name": name}, {"$set": doc})
    else:
        doc["columns"] = payload.get("columns") or []
        doc["rows"] = payload.get("rows") or []
        doc["window"] = payload.get("window")
        doc["created_at"] = now
        coll.insert_one(doc)
    return get_report(name) or doc


def patch_report(name: str, updates: dict[str, Any]) -> dict[str, Any]:
    coll = reports_collection()
    existing = coll.find_one({"name": name})
    if not existing:
        raise ValueError(f"Unknown report '{name}'.")
    allowed: dict[str, Any] = {}
    if "title" in updates:
        allowed["title"] = str(updates["title"])
    if "description" in updates:
        allowed["description"] = str(updates["description"])
    if "enabled" in updates:
        allowed["enabled"] = bool(updates["enabled"])
    if "saved" in updates:
        allowed["saved"] = bool(updates["saved"])
    if "prompt" in updates:
        allowed["prompt"] = updates["prompt"]
    if not allowed:
        raise ValueError("No valid fields to update.")
    allowed["updated_at"] = _now()
    coll.update_one({"name": name}, {"$set": allowed})
    return get_report(name) or {}


def delete_report(name: str) -> None:
    coll = reports_collection()
    existing = coll.find_one({"name": name})
    if not existing:
        raise ValueError(f"Unknown report '{name}'.")
    if existing.get("builtin"):
        raise ValueError("Cannot delete builtin reports.")
    coll.delete_one({"name": name})


def refresh_report(
    name: str,
    *,
    start: datetime,
    end: datetime,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Run the report generator and persist a fresh snapshot."""
    coll = reports_collection()
    existing = coll.find_one({"name": name})
    if not existing:
        raise ValueError(f"Unknown report '{name}'.")
    generator = existing.get("generator") or {}
    if generator.get("type") != "module":
        raise ValueError(f"Report '{name}' has unsupported generator type.")
    module_name = validate_module_name(str(generator.get("module")))
    try:
        result = run_generator_module(module_name, start=start, end=end)
    except ReadOnlyError:
        raise
    window = {"start_date": start_date, "end_date": end_date}
    coll.update_one(
        {"name": name},
        {
            "$set": {
                "columns": result["columns"],
                "rows": result["rows"],
                "window": window,
                "updated_at": _now(),
            }
        },
    )
    return get_report_snapshot(name) or {}
