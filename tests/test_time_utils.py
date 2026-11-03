"""Tests for UTC storage / Pacific display helpers."""

from datetime import datetime, timezone

from alab_management.utils.time import (
    CUTOVER_UTC,
    format_pacific,
    interpret_stored_datetime,
    utc_now,
)


def test_utc_now_is_naive_utc_shaped():
    before = datetime.now(timezone.utc).replace(tzinfo=None)
    got = utc_now()
    after = datetime.now(timezone.utc).replace(tzinfo=None)
    assert got.tzinfo is None
    assert before <= got <= after


def test_interpret_pre_cutover_as_pacific():
    # 4:12 PM Pacific wall clock stored as naive pre-cutover
    stored = datetime(2026, 11, 2, 16, 12, 27)
    assert stored < CUTOVER_UTC
    instant = interpret_stored_datetime(stored)
    assert instant is not None
    assert instant.tzinfo == timezone.utc
    # PST (UTC-8) on that date after DST end
    assert instant == datetime(2026, 11, 3, 0, 12, 27, tzinfo=timezone.utc)


def test_interpret_post_cutover_as_utc():
    stored = datetime(2026, 11, 3, 2, 0, 0)
    assert stored >= CUTOVER_UTC
    instant = interpret_stored_datetime(stored)
    assert instant == datetime(2026, 11, 3, 2, 0, 0, tzinfo=timezone.utc)


def test_format_pacific_pre_and_post():
    pre = format_pacific(datetime(2026, 11, 2, 16, 12, 27))
    assert "2026-11-02" in pre
    assert "4:12:27 PM" in pre
    assert pre.endswith("PT")

    # 02:00 UTC -> 6:00 PM PT previous calendar day? Nov 3 02:00 UTC = Nov 2 6:00 PM PST
    post = format_pacific(datetime(2026, 11, 3, 2, 0, 0))
    assert "6:00:00 PM" in post
    assert post.endswith("PT")


def test_interpret_none():
    assert interpret_stored_datetime(None) is None
    assert format_pacific(None) == ""
