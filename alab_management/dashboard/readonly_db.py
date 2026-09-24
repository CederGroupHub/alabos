"""Read-only Mongo wrappers for Data report generators."""

from __future__ import annotations

from typing import Any

from pymongo import collection, database

_WRITE_METHODS = frozenset(
    {
        "insert_one",
        "insert_many",
        "update_one",
        "update_many",
        "replace_one",
        "delete_one",
        "delete_many",
        "find_one_and_update",
        "find_one_and_replace",
        "find_one_and_delete",
        "bulk_write",
        "aggregate",  # can include $out / $merge; block for safety in v1
        "drop",
        "rename",
        "create_index",
        "create_indexes",
        "drop_index",
        "drop_indexes",
    }
)


class ReadOnlyError(PermissionError):
    """Raised when a report generator attempts a write against lab data."""


class ReadOnlyCollection:
    """Proxy that allows find/count/distinct but rejects mutating Collection APIs."""

    def __init__(self, coll: collection.Collection):
        self._coll = coll

    def __getattr__(self, name: str) -> Any:
        if name in _WRITE_METHODS:
            raise ReadOnlyError(
                f"Report generators cannot call Collection.{name} (read-only)."
            )
        return getattr(self._coll, name)

    def __getitem__(self, name: str) -> Any:
        raise ReadOnlyError("Report generators cannot subscript collections.")


class ReadOnlyDatabase:
    """Proxy Database that yields ReadOnlyCollection for all names."""

    def __init__(self, db: database.Database):
        self._db = db

    def __getattr__(self, name: str) -> Any:
        if name in {"drop_collection", "create_collection", "command"}:
            raise ReadOnlyError(
                f"Report generators cannot call Database.{name} (read-only)."
            )
        attr = getattr(self._db, name)
        return attr

    def __getitem__(self, name: str) -> ReadOnlyCollection:
        return ReadOnlyCollection(self._db[name])

    def get_collection(self, name: str) -> ReadOnlyCollection:
        return ReadOnlyCollection(self._db.get_collection(name))

    @property
    def name(self) -> str:
        return self._db.name
