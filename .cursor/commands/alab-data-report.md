---
description: Create, change, or delete a reusable ALab Data page report (pairs with alab-data-reports MCP)
---

# ALab Data page report (`/alab-data-report`)

Ship a report the operator opens on **Data** (8895): dropdown → table/CSV.
Chat is not the deliverable. Use MCP **`alab-data-reports`** + this slash command (same name family).

Also see `docs/data-reports-cursor.md`.

## Checklist

```
- [ ] Intent: create | change | delete
- [ ] Chose / resolved snake_case slug
- [ ] Wrote or edited user_reports/<slug>.py (create/change) OR deleted file (delete)
- [ ] Used find_union when names live in both DBs
- [ ] Read-only only (no lab writes)
- [ ] MCP register / update / delete + refresh as needed
- [ ] Told user: Data page will show the catalog change shortly
```

## Intent

Infer from the user message:

1. **create** — new table
2. **change** — edit an existing report’s generator and/or metadata
3. **delete** — remove a custom report

MCP tools (enable **`alab-data-reports`** via `.cursor/mcp.json`): `list_data_reports`, `register_data_report`, `update_data_report`, `delete_data_report`, `refresh_data_report`, `get_data_report_rows`.

Dashboard must be reachable (`ALAB_DASHBOARD_BASE`, default `http://127.0.0.1:8895`).

**Host rule:** Run **`/alab-data-report`** and the **`alab-data-reports`** MCP **only on the computer that serves AlabOS** (the lab machine running port 8895). Do not author reports from a remote laptop against a networked dashboard — the generator `.py` must land on the same filesystem the dashboard imports.

## Create

1. Write `alab_management/dashboard/user_reports/<slug>.py` with:

```python
from datetime import datetime
from typing import Any

from alab_management.dashboard.report_db import find_union

def run(*, start: datetime, end: datetime, live_db: Any, completed_db: Any) -> dict:
    docs = find_union(
        "samples",
        {"created_at": {"$gte": start, "$lt": end}},
        live_db=live_db,
        completed_db=completed_db,
    )
    return {
        "columns": [
            {"key": "name", "label": "Sample"},
            {"key": "created_at", "label": "Created"},
        ],
        "rows": [
            {"name": d.get("name"), "created_at": d.get("created_at")}
            for d in docs
        ],
    }
```

Rules: max **5000** rows; read-only; UTF-8 (no BOM); prefer Write/StrReplace — no PowerShell `Set-Content`/`Out-File`.

2. `register_data_report(name=slug, title=..., saved=true, module=slug)`
3. `refresh_data_report(name=slug)` (optional date window)
4. Tell operator: **Data** → select report → **Download CSV** (catalog auto-refreshes).

## Change

1. `list_data_reports` → resolve slug by name/title.
2. Never edit builtin modules: `sample_report`, `sample_summary`, `powder_dosing_actuals`, `task_outcome_log`.
3. Edit `user_reports/<slug>.py` and/or `update_data_report`.
4. `refresh_data_report`.

## Delete

1. Refuse builtins.
2. `delete_data_report(name=slug)`.
3. Delete `user_reports/<slug>.py` if present.

## Do not

- Finish with only a chat table or `agent_temp` CSV
- `exec` Python stored in Mongo
- Use the removed Data-page “Ask for a report” / `report_jobs` API

## User request

$ARGUMENTS
