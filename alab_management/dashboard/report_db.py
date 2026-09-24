"""Helpers for Data report generators (dual-DB reads)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from alab_management.utils.data_objects import get_collection, get_completed_collection


def doc_sort_ts(doc: dict[str, Any]) -> datetime:
    return doc.get("last_updated") or doc.get("created_at") or datetime.min


def find_union(
    collection_name: str,
    query: dict[str, Any] | None = None,
    *,
    projection: dict[str, Any] | None = None,
    live_db: Any = None,
    completed_db: Any = None,
) -> list[dict[str, Any]]:
    """Find across live + completed; newer doc wins on ``_id`` collision."""
    query = query or {}
    by_id: dict[str, dict[str, Any]] = {}

    def _ingest(docs) -> None:
        for doc in docs:
            sid = str(doc.get("_id"))
            if sid not in by_id or doc_sort_ts(doc) >= doc_sort_ts(by_id[sid]):
                by_id[sid] = doc

    if live_db is not None:
        coll = live_db[collection_name]
        _ingest(coll.find(query, projection) if projection else coll.find(query))
    else:
        coll = get_collection(collection_name)
        _ingest(coll.find(query, projection) if projection else coll.find(query))

    try:
        if completed_db is not None:
            coll = completed_db[collection_name]
            _ingest(coll.find(query, projection) if projection else coll.find(query))
        else:
            coll = get_completed_collection(collection_name)
            _ingest(coll.find(query, projection) if projection else coll.find(query))
    except (ValueError, KeyError):
        pass

    return list(by_id.values())
