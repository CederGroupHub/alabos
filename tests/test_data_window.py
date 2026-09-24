"""Tests for Data page date-window parsing."""

from datetime import datetime

import pytest

from alab_management.dashboard.routes import data as data_routes


def test_format_range_label_full_month() -> None:
    assert (
        data_routes._format_range_label(datetime(2026, 9, 1), datetime(2026, 9, 30))
        == "September 2026"
    )


def test_format_range_label_partial_month() -> None:
    assert (
        data_routes._format_range_label(datetime(2026, 9, 1), datetime(2026, 9, 15))
        == "Sep 1–15, 2026"
    )


def test_window_from_params_custom_inclusive_end(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeCol:
        def find_one(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(data_routes, "_get_history_collection", lambda _name: _FakeCol())
    window = data_routes._window_from_params(start="2026-09-01", end="2026-09-15")
    assert window["start"] == datetime(2026, 9, 1)
    assert window["end"] == datetime(2026, 9, 16)
    assert window["start_date"] == "2026-09-01"
    assert window["end_date"] == "2026-09-15"
    assert window["month"] is None
    assert window["label"] == "Sep 1–15, 2026"


def test_window_from_params_month_still_works(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeCol:
        def find_one(self, *_args, **_kwargs):
            return {"_id": 1}

    monkeypatch.setattr(data_routes, "_get_history_collection", lambda _name: _FakeCol())
    window = data_routes._window_from_params(month="2026-08")
    assert window["month"] == "2026-08"
    assert window["start_date"] == "2026-08-01"
    assert window["end_date"] == "2026-08-31"
    assert window["label"] == "August 2026"


def test_window_from_params_rejects_inverted_range() -> None:
    with pytest.raises(ValueError, match="end must be on or after start"):
        data_routes._window_from_params(start="2026-09-15", end="2026-09-01")
