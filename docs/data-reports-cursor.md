# Custom Data reports (Cursor `/alab-data-report` + MCP `alab-data-reports`)

Operators create, change, or delete custom tables on the **Data** page from the **Cursor agent window** using slash command **`/alab-data-report`** (see `.cursor/commands/alab-data-report.md`). The agent writes a **read-only** Python generator and registers it via the **alab-data-reports** MCP (same HTTP APIs as the dashboard). The Data page shows a snapshot, can **Refresh**, and can **Download CSV**.

There is no in-UI “Ask for a report” Cursor box anymore.

## Setup

1. Enable the MCP server (repo [`.cursor/mcp.json`](../.cursor/mcp.json)):

```json
{
  "mcpServers": {
    "alab-data-reports": {
      "command": "python",
      "args": ["-m", "alab_management.mcp_data_reports"],
      "env": { "ALAB_DASHBOARD_BASE": "http://127.0.0.1:8895" }
    }
  }
}
```

2. AlabOS dashboard must be reachable at `ALAB_DASHBOARD_BASE` (default `http://127.0.0.1:8895`).

3. In Cursor: `/alab-data-report` then describe create / change / delete.

Optional: `python -m alab_management.mcp_data_reports` or console script `alab-data-reports-mcp`.

## Contract

Package: `alab_management/dashboard/user_reports/`

```python
# alab_management/dashboard/user_reports/my_report.py
from datetime import datetime
from typing import Any

def run(*, start: datetime, end: datetime, live_db: Any, completed_db: Any) -> dict:
    """Read-only. Return columns + rows (max 5000 rows)."""
    samples = list(live_db["samples"].find({"created_at": {"$gte": start, "$lt": end}}))
    # Prefer alab_management.dashboard.report_db.find_union for Alab + Alab(completed).
    return {
        "columns": [
            {"key": "name", "label": "Sample"},
            {"key": "created_at", "label": "Created"},
        ],
        "rows": [
            {"name": s.get("name"), "created_at": s.get("created_at")}
            for s in samples
        ],
    }
```

Rules:

- **Read lab data only** (`samples`, `tasks`, `experiment`, …). No inserts/updates/deletes.
- `live_db` / `completed_db` are read-only wrappers; writes raise.
- Module name: lowercase snake_case; loaded only from `user_reports`.
- Return at most **5000** rows.
- Write files as **UTF-8** (prefer Write/StrReplace; avoid PowerShell `Set-Content` / `Out-File`).

## Registry document (`Alab.data_reports`)

```js
{
  "name": "my_report",
  "title": "My Report",
  "description": "…",
  "enabled": true,
  "saved": true,
  "builtin": false,
  "generator": { "type": "module", "module": "my_report" },
  "row_detail": null,
  "prompt": "optional original user ask",
  "columns": [],
  "rows": [],
  "window": null
}
```

Register via MCP `register_data_report` or `POST /api/data/reports`. Then open Data → pick the report (catalog polls) → Refresh if needed.

## MCP tools

| Tool | Maps to |
|------|---------|
| `list_data_reports` | `GET /api/data/reports` |
| `register_data_report` | `POST /api/data/reports` |
| `update_data_report` | `PATCH /api/data/reports/<name>` |
| `delete_data_report` | `DELETE /api/data/reports/<name>` |
| `refresh_data_report` | `POST /api/data/reports/<name>/refresh` |
| `get_data_report_rows` | `GET /api/data/reports/<name>/rows` |

## API (dashboard)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/data/reports` | Catalog (no rows) |
| GET | `/api/data/reports/<name>/rows` | Snapshot |
| POST | `/api/data/reports/<name>/refresh?start=&end=` | Re-run generator |
| GET | `/api/data/reports/<name>.csv` | CSV of snapshot |
| POST | `/api/data/reports` | Register metadata |
| PATCH | `/api/data/reports/<name>` | Save flag / title |
| DELETE | `/api/data/reports/<name>` | Non-builtins only |

Builtins (`sample_report`, `sample_summary`, `powder_dosing_actuals`, `task_outcome_log`) are seeded automatically and must not be overwritten or deleted via `/alab-data-report`.

## Helper for both databases

```python
from alab_management.dashboard.report_db import find_union

docs = find_union(
    "samples",
    {"created_at": {"$gte": start, "$lt": end}},
    live_db=live_db,
    completed_db=completed_db,
)
```

## UI behavior

- **Create / change / delete** = Cursor `/alab-data-report` + MCP `alab-data-reports` (not an in-page text box).
- Catalog **polls** while Data is open so new/updated/removed reports appear quickly.
- **Open** = last snapshot (instant).
- **Refresh** = re-import the generator module from disk and call `run(...)` with the page date range.
- **Save** = mark `saved: true` (does not recompute).
- **CSV** = current snapshot.
- **Fullscreen** = expand the table for a large view.

Browser reload alone only shows the **last saved snapshot**. After editing a generator, click **Refresh** (or let `/alab-data-report` call `refresh_data_report`) to pick up the new code.

## Multi-user / lab PC visibility

**Policy:** Operators may only run `/alab-data-report` and the `alab-data-reports` MCP **on the computer that serves AlabOS** (the host bound to port 8895). Use `ALAB_DASHBOARD_BASE=http://127.0.0.1:8895` on that machine.

Anyone else browsing `http://<lab-ip>:8895` then sees the same catalog and snapshots automatically (shared Mongo + shared `user_reports/` on that host). Do not author reports from a remote laptop pointed at `192.168…:8895` — the generator file would not exist on the AlabOS filesystem and Refresh would fail.