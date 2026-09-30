"""ALab Data reports MCP — stdio tools wrapping dashboard /api/data/reports."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_DASHBOARD_BASE = "http://127.0.0.1:8895"
PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "alab-data-reports"
SERVER_VERSION = "1.0.0"


def dashboard_base() -> str:
    """Return the AlabOS dashboard base URL (no trailing slash)."""
    return (os.environ.get("ALAB_DASHBOARD_BASE") or DEFAULT_DASHBOARD_BASE).rstrip("/")


def _http_json(
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    query: dict[str, str] | None = None,
) -> dict[str, Any]:
    url = dashboard_base() + path
    if query:
        url += "?" + urllib.parse.urlencode({k: v for k, v in query.items() if v})
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {"status": "success"}
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:  # noqa: BLE001
            payload = {"status": "error", "errors": str(exc)}
        raise RuntimeError(
            payload.get("errors") or payload.get("error") or str(exc)
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Cannot reach dashboard at {dashboard_base()}: {exc.reason}. "
            "Is AlabOS on 8895 running? Set ALAB_DASHBOARD_BASE if needed."
        ) from exc


def list_data_reports() -> dict[str, Any]:
    """List enabled Data report registry entries (no row payloads)."""
    return _http_json("GET", "/api/data/reports")


def register_data_report(
    *,
    name: str,
    title: str,
    description: str = "",
    prompt: str = "",
    module: str | None = None,
    enabled: bool = True,
    saved: bool = True,
    created_by: str = "data_report_mcp",
) -> dict[str, Any]:
    """Register (upsert) a module-backed report. Write user_reports/<slug>.py first."""
    slug = module or name
    body = {
        "name": name,
        "title": title,
        "description": description,
        "enabled": enabled,
        "saved": saved,
        "generator": {"type": "module", "module": slug},
        "prompt": prompt,
        "created_by": created_by,
    }
    return _http_json("POST", "/api/data/reports", body=body)


def update_data_report(name: str, **fields: Any) -> dict[str, Any]:
    """PATCH metadata for an existing report (title, description, enabled, saved, prompt)."""
    allowed = {
        k: v
        for k, v in fields.items()
        if k in ("title", "description", "enabled", "saved", "prompt", "generator")
        and v is not None
    }
    if not allowed:
        raise ValueError("No update fields provided.")
    return _http_json("PATCH", f"/api/data/reports/{urllib.parse.quote(name)}", body=allowed)


def delete_data_report(name: str) -> dict[str, Any]:
    """Delete a non-builtin report from the registry. Also delete user_reports/<slug>.py."""
    return _http_json("DELETE", f"/api/data/reports/{urllib.parse.quote(name)}")


def refresh_data_report(
    name: str,
    *,
    start: str | None = None,
    end: str | None = None,
    month: str | None = None,
) -> dict[str, Any]:
    """Re-run the generator and store a snapshot."""
    query: dict[str, str] = {}
    if month:
        query["month"] = month
    if start and end:
        query["start"] = start
        query["end"] = end
    return _http_json(
        "POST",
        f"/api/data/reports/{urllib.parse.quote(name)}/refresh",
        query=query or None,
    )


def get_data_report_rows(name: str) -> dict[str, Any]:
    """Return the stored snapshot for a report."""
    return _http_json("GET", f"/api/data/reports/{urllib.parse.quote(name)}/rows")


TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "list_data_reports",
        "description": "List enabled ALab Data page reports (name, title, builtin, saved).",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "register_data_report",
        "description": (
            "Register or upsert a custom Data report after writing "
            "alab_management/dashboard/user_reports/<slug>.py. "
            "generator.module must match the file stem."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "snake_case slug"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "prompt": {"type": "string"},
                "module": {
                    "type": "string",
                    "description": "Generator module stem; defaults to name",
                },
                "enabled": {"type": "boolean", "default": True},
                "saved": {"type": "boolean", "default": True},
                "created_by": {"type": "string", "default": "data_report_mcp"},
            },
            "required": ["name", "title"],
            "additionalProperties": False,
        },
    },
    {
        "name": "update_data_report",
        "description": "Update metadata on an existing non-builtin report (PATCH).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "prompt": {"type": "string"},
                "enabled": {"type": "boolean"},
                "saved": {"type": "boolean"},
            },
            "required": ["name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "delete_data_report",
        "description": (
            "Delete a non-builtin report from Alab.data_reports. "
            "Also delete user_reports/<slug>.py with the file tools."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "refresh_data_report",
        "description": "Re-run the report generator and update the stored snapshot.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "start": {"type": "string", "description": "YYYY-MM-DD"},
                "end": {"type": "string", "description": "YYYY-MM-DD"},
                "month": {"type": "string", "description": "YYYY-MM"},
            },
            "required": ["name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_data_report_rows",
        "description": "Fetch the current stored snapshot (columns + rows) for a report.",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
            "additionalProperties": False,
        },
    },
]


def call_tool(name: str, arguments: dict[str, Any] | None) -> Any:
    """Dispatch an MCP tool name to the matching HTTP helper."""
    args = arguments or {}
    if name == "list_data_reports":
        return list_data_reports()
    if name == "register_data_report":
        return register_data_report(**args)
    if name == "update_data_report":
        report_name = args.pop("name")
        return update_data_report(report_name, **args)
    if name == "delete_data_report":
        return delete_data_report(args["name"])
    if name == "refresh_data_report":
        return refresh_data_report(
            args["name"],
            start=args.get("start"),
            end=args.get("end"),
            month=args.get("month"),
        )
    if name == "get_data_report_rows":
        return get_data_report_rows(args["name"])
    raise ValueError(f"Unknown tool: {name}")


def _tool_result(payload: Any, *, is_error: bool = False) -> dict[str, Any]:
    text = payload if isinstance(payload, str) else json.dumps(payload, default=str, indent=2)
    return {
        "content": [{"type": "text", "text": text}],
        "isError": is_error,
    }


def handle_message(msg: dict[str, Any]) -> dict[str, Any] | None:
    """Handle one JSON-RPC message; return a response or None for notifications."""
    method = msg.get("method")
    msg_id = msg.get("id")
    params = msg.get("params") or {}

    if method == "notifications/initialized":
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        }

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"tools": TOOL_SPECS},
        }

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            result = call_tool(tool_name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": _tool_result(result),
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": _tool_result(str(exc), is_error=True),
            }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

    if msg_id is None:
        return None

    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> None:
    """Run MCP over stdin/stdout (one JSON-RPC object per line)."""
    # Ensure stdout is used only for protocol; log to stderr.
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as exc:
            err = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
            }
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()
            continue
        response = handle_message(msg)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
