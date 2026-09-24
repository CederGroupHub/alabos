# Custom Data reports (Cursor generators)

Operators ask Cursor for a custom table on the **Data** page. Cursor writes a **read-only** Python generator and registers it in Mongo. The dashboard shows a snapshot, can **Refresh** (re-run for fresh data), and can **Save** the registry entry for reuse.

## Data page “Ask for a report” (Cursor SDK)

The Data UI includes a freeform box that starts a **local** Cursor agent against this repo. The agent is always given the pipeline instructions below (generator module + registry upsert).

### Server setup

1. Install the optional SDK package in the management env:

```bash
pip install "alab_management[data_reports]"
# or: pip install cursor-sdk
```

2. Set a Cursor API key on the **dashboard process** (not in git):

```powershell
$env:CURSOR_API_KEY = "cursor_..."
```

Create a key at [Cursor Dashboard → Integrations](https://cursor.com/dashboard/integrations). Restart the dashboard after setting the key so the process inherits it.

Optional env vars:

```text
ALAB_MANAGEMENT_ROOT=C:\path\to\alab_management   # agent cwd; default = package repo root
ALAB_DASHBOARD_BASE=http://127.0.0.1:8895          # where the agent POSTs /api/data/reports
CURSOR_DATA_REPORT_MODEL=composer-2.5
```

3. On the Data page: describe the table → **Submit** → wait for status `succeeded` → catalog reloads → **Refresh** the new report.

If `CURSOR_API_KEY` or `cursor-sdk` is missing, Submit returns HTTP 503 with a clear error.

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

Insert via Mongo MCP or `POST /api/data/reports`. Then open Data → pick the report → **Refresh**.

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
| POST | `/api/data/report_jobs` | Start Cursor agent job (`{prompt}`) |
| GET | `/api/data/report_jobs/<id>` | Job status + log |
| GET | `/api/data/report_jobs/current` | Latest/active job |

Builtins (`sample_report`, `sample_summary`, `powder_dosing_actuals`, `task_outcome_log`) are seeded automatically.

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

- **Ask for a report** = local Cursor agent writes `user_reports/<slug>.py` + registers it; then Reload catalog / select / Refresh.
- **Open** = last snapshot (instant).
- **Refresh** = re-import the generator module from disk (no AlabOS restart) and call `run(...)` with the page date range → update snapshot.
- **Save** = mark `saved: true` (does not recompute).
- **CSV** = current snapshot.

Browser reload alone only shows the **last saved snapshot**. After editing a generator (columns, queries, etc.), click **Refresh** on that panel to pick up the new code.

### Manual smoke (after key + SDK install)

Submit: “samples created in the date range with name and created_at” → new dropdown entry → Refresh → rows.
