"""Cursor-authored Data report generators.

Each module must define:

    def run(*, start, end, live_db, completed_db) -> dict:
        return {"columns": [{"key", "label"}, ...], "rows": [dict, ...]}

Generators must only *read* lab data. The runner injects read-only DB handles.
"""

from __future__ import annotations
