"""Tests for Data report registry, read-only DB, and module runner."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from alab_management.dashboard import data_reports as reports
from alab_management.dashboard.readonly_db import ReadOnlyCollection, ReadOnlyDatabase, ReadOnlyError


def test_validate_module_name_accepts_snake_case() -> None:
    assert reports.validate_module_name("sample_report") == "sample_report"


def test_validate_module_name_rejects_path() -> None:
    with pytest.raises(ValueError):
        reports.validate_module_name("../evil")
    with pytest.raises(ValueError):
        reports.validate_module_name("Foo")


def test_load_user_report_module_loads_builtin() -> None:
    module = reports.load_user_report_module("sample_report")
    assert callable(module.run)


def test_load_user_report_module_reloads_from_disk() -> None:
    """Edits must be visible on the next load without process restart."""
    module = reports.load_user_report_module("sample_summary")
    module._stale_marker = "old"  # type: ignore[attr-defined]
    reloaded = reports.load_user_report_module("sample_summary")
    assert not hasattr(reloaded, "_stale_marker")
    assert callable(reloaded.run)


def test_load_user_report_module_rejects_outside_package(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_import(name: str):
        mod = MagicMock()
        mod.__name__ = "os.path"
        mod.run = lambda **kwargs: {"columns": [{"key": "a", "label": "A"}], "rows": []}
        return mod

    monkeypatch.setattr(reports.importlib, "import_module", fake_import)
    with pytest.raises(ValueError, match="outside"):
        reports.load_user_report_module("sample_report")


def test_readonly_collection_blocks_writes() -> None:
    coll = MagicMock()
    proxy = ReadOnlyCollection(coll)
    proxy.find({"a": 1})
    coll.find.assert_called_once()
    with pytest.raises(ReadOnlyError):
        proxy.insert_one({"a": 1})
    with pytest.raises(ReadOnlyError):
        proxy.delete_many({})


def test_readonly_database_returns_readonly_collections() -> None:
    db = MagicMock()
    db.__getitem__.side_effect = lambda name: MagicMock(name=name)
    proxy = ReadOnlyDatabase(db)
    coll = proxy["samples"]
    assert isinstance(coll, ReadOnlyCollection)
    with pytest.raises(ReadOnlyError):
        proxy.drop_collection("samples")


def test_normalize_report_result_enforces_row_cap() -> None:
    columns = [{"key": "name", "label": "Name"}]
    rows = [{"name": str(i)} for i in range(reports.MAX_REPORT_ROWS + 1)]
    with pytest.raises(ValueError, match="max rows"):
        reports.normalize_report_result({"columns": columns, "rows": rows})


def test_normalize_report_result_truncates_long_cells() -> None:
    columns = [{"key": "name", "label": "Name"}]
    long = "x" * (reports.MAX_CELL_CHARS + 50)
    out = reports.normalize_report_result(
        {"columns": columns, "rows": [{"name": long}]}
    )
    assert len(out["rows"][0]["name"]) == reports.MAX_CELL_CHARS + 1  # includes ellipsis


def test_delete_report_blocks_builtins(monkeypatch: pytest.MonkeyPatch) -> None:
    coll = MagicMock()
    coll.find_one.return_value = {"name": "sample_report", "builtin": True}
    monkeypatch.setattr(reports, "reports_collection", lambda: coll)
    with pytest.raises(ValueError, match="builtin"):
        reports.delete_report("sample_report")


def test_run_generator_module_sample_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    live = MagicMock()
    completed = MagicMock()
    live_coll = MagicMock()
    live_coll.find.return_value = [
        {
            "_id": "abc",
            "name": "S1",
            "created_at": datetime(2026, 9, 1),
            "metadata": {"target": "x"},
        }
    ]
    live.__getitem__.return_value = live_coll
    completed.__getitem__.return_value = MagicMock(find=MagicMock(return_value=[]))

    monkeypatch.setattr(
        reports,
        "_read_only_handles",
        lambda: (live, completed),
    )
    # find_union uses live_db[name].find — our MagicMock live is not ReadOnlyDatabase
    # but sample_summary.run will call find_union which uses live_db[collection].
    # Patch find_union instead for a tight unit test.
    from alab_management.dashboard.user_reports import sample_summary

    monkeypatch.setattr(
        "alab_management.dashboard.user_reports.sample_summary.find_union",
        lambda *args, **kwargs: [
            {
                "_id": "abc",
                "name": "S1",
                "created_at": datetime(2026, 9, 1),
                "metadata": {"target": "x"},
            }
        ],
    )
    result = sample_summary.run(
        start=datetime(2026, 9, 1),
        end=datetime(2026, 10, 1),
        live_db=live,
        completed_db=completed,
    )
    assert result["columns"][0]["key"] == "sample_id"
    assert result["rows"][0]["name"] == "S1"
