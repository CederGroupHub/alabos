# AlabOS timestamps

## Policy

| Layer | Behavior |
|-------|----------|
| Mongo writes (after cutover) | Naive **UTC** via `alab_management.utils.time.utc_now()` |
| Mongo docs (before cutover) | Left as-is: naive **Pacific wall clock** |
| Operator GUI / formatted reports | Always **California** time (`format_pacific` / cutover-aware client) |
| Agents / ObjectId comparison | Use `interpret_stored_datetime` |

**Cutover:** `CUTOVER_UTC` / `CUTOVER_UTC_ISO` in `alab_management/utils/time.py` (`2026-11-03T01:30:00Z`). Documents with stored naive values **before** that instant are interpreted as Pacific; **on or after**, as UTC.

## Rules for code

- Persist with `utc_now()`, never bare `datetime.now()` for Mongo fields (`created_at`, `last_updated`, `position_history.at`, etc.).
- Do not migrate historical documents.
- Do not show raw `…Z` / “UTC” stamps in normal operator UI copy.

## Dashboard

`Experiments.js` `timestampInLocale` is cutover-aware: pre-cutover keeps the legacy offset correction so remembered times stay stable; post-cutover uses normal locale formatting of real UTC.
