"""Tiny in-process notification sink — stand-in for an email/push system.

A real app would call out to a mailer plugin; here we just append to a
list so the test suite can assert that the background task fired.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(slots=True, frozen=True)
class Notification:
    kind: str
    payload: dict[str, object]
    at: datetime


_log: list[Notification] = []


def record(kind: str, **payload: object) -> None:
    _log.append(Notification(kind=kind, payload=payload, at=datetime.now(timezone.utc)))


def history() -> list[Notification]:
    return list(_log)


def clear() -> None:
    _log.clear()
