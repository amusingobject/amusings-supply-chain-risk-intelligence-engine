"""UTC timestamp helpers. Unknown remains unknown."""

from __future__ import annotations

from datetime import datetime, timezone


def parse_utc(value: str | None) -> datetime | None:
    if value is None or value == "":
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def lte(left: str | None, right: str | None) -> bool | None:
    a = parse_utc(left)
    b = parse_utc(right)
    if a is None or b is None:
        return None
    return a <= b


def windows_overlap(start_a: str | None, end_a: str | None, start_b: str | None, end_b: str | None) -> bool:
    a0 = parse_utc(start_a)
    b0 = parse_utc(start_b)
    if a0 is None or b0 is None:
        return False
    a1 = parse_utc(end_a)
    b1 = parse_utc(end_b)
    a_end = a1 or datetime.max.replace(tzinfo=timezone.utc)
    b_end = b1 or datetime.max.replace(tzinfo=timezone.utc)
    return a0 <= b_end and b0 <= a_end
