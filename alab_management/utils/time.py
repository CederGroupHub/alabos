"""UTC storage and Pacific display helpers for AlabOS timestamps.

After ``CUTOVER_UTC``, persisted datetimes are naive UTC. Older documents stored
naive Pacific wall-clock values. Operator-facing surfaces should always format
via ``format_pacific`` / cutover-aware client helpers so California time stays
visible in the GUI.
"""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# First moment at which new writes are naive UTC (not Pacific wall clock).
# Bump only if intentionally redefining the cutover for a fresh deploy narrative.
CUTOVER_UTC = datetime(2026, 11, 3, 1, 30, 0)  # naive UTC ≈ 2026-11-02 5:30 PM PT

PACIFIC_TZ = ZoneInfo("America/Los_Angeles")
UTC = timezone.utc

# ISO for dashboard clients (same instant as CUTOVER_UTC, with Z).
CUTOVER_UTC_ISO = "2026-11-03T01:30:00.000Z"


def utc_now() -> datetime:
    """Naive UTC now for Mongo write paths (BSON dates without tzinfo)."""
    return datetime.now(UTC).replace(tzinfo=None)


def interpret_stored_datetime(dt: datetime | None) -> datetime | None:
    """Return an aware UTC instant for a value read from Mongo.

    Pre-cutover naive values are treated as America/Los_Angeles wall clock.
    Post-cutover naive values are treated as UTC. Aware inputs are converted to UTC.
    """
    if dt is None:
        return None
    if not isinstance(dt, datetime):
        raise TypeError(f"expected datetime, got {type(dt)!r}")

    if dt.tzinfo is not None:
        return dt.astimezone(UTC)

    naive = dt.replace(tzinfo=None)
    if naive < CUTOVER_UTC:
        return naive.replace(tzinfo=PACIFIC_TZ).astimezone(UTC)
    return naive.replace(tzinfo=UTC)


def format_pacific(dt: datetime | None) -> str:
    """Format a stored or aware datetime for operators (Pacific wall clock)."""
    instant = interpret_stored_datetime(dt)
    if instant is None:
        return ""
    local = instant.astimezone(PACIFIC_TZ)
    hour_12 = local.strftime("%I").lstrip("0") or "12"
    return f"{local.strftime('%Y-%m-%d')} {hour_12}{local.strftime(':%M:%S %p')} PT"
