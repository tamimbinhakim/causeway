"""Tiny crontab parser.

Five fields: minute hour day-of-month month day-of-week. Each field is one
of: ``*``, an integer, a comma list ``1,3,5``, or a step ``*/N``. That's
all we need for the in-process reference adapter — production adapters
delegate to their own scheduler.
"""

from __future__ import annotations

from datetime import datetime, timedelta

_FIELD_RANGES = [
    (0, 59),  # minute
    (0, 23),  # hour
    (1, 31),  # day of month
    (1, 12),  # month
    (0, 6),  # day of week (0=Mon...6=Sun for simplicity)
]


def _parse_field(spec: str, lo: int, hi: int) -> set[int]:
    if spec == "*":
        return set(range(lo, hi + 1))
    if spec.startswith("*/"):
        step = int(spec[2:])
        return set(range(lo, hi + 1, step))
    out: set[int] = set()
    for piece in spec.split(","):
        out.add(int(piece))
    return out


def _matches(expr: str, now: datetime) -> bool:
    parts = expr.split()
    if len(parts) != 5:
        msg = f"cron expr must be 5 fields: {expr!r}"
        raise ValueError(msg)
    minute, hour, dom, month, dow = (
        _parse_field(p, *_FIELD_RANGES[i]) for i, p in enumerate(parts)
    )
    return (
        now.minute in minute
        and now.hour in hour
        and now.day in dom
        and now.month in month
        # weekday(): Mon=0..Sun=6 — matches our field convention.
        and now.weekday() in dow
    )


def next_fire(expr: str, after: datetime) -> float:
    """Seconds until the next minute that matches ``expr`` after ``after``.

    Scans minute-by-minute up to 31 days ahead — fine for the in-memory
    reference adapter. If no match is found, raises.
    """
    candidate = (after + timedelta(minutes=1)).replace(second=0, microsecond=0)
    end = candidate + timedelta(days=31)
    while candidate < end:
        if _matches(expr, candidate):
            return (candidate - after).total_seconds()
        candidate += timedelta(minutes=1)
    msg = f"no cron match within 31 days for {expr!r}"
    raise ValueError(msg)
