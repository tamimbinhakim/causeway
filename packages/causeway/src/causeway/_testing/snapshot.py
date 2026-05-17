"""Inline snapshot subsystem.

``snapshot(value)`` participates in ``==`` against a value walked via
``expect(...).body...``. On a match — recorded value structurally equals
actual — the assertion passes; on a mismatch, behaviour depends on
whether ``--update-snapshots`` was passed to pytest:

- without the flag: raise :class:`ScenarioAssertionError` with a diff.
- with the flag: record a pending edit for the file-level rewriter to
  apply at session end.

``snapshot()`` (no recorded value) is "fresh" — fails without the flag,
records the actual as the new value with the flag.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from causeway._testing.errors import ScenarioAssertionError
from causeway._testing.registry import current_registry

_UNSET: Any = object()


class _AnyMatch:
    """Singleton ``...``-like wildcard used inside snapshot literals."""

    def __repr__(self) -> str:
        return "..."

    def __eq__(self, _other: object) -> bool:
        return True

    def __hash__(self) -> int:
        return id(self)


Ellipsis: _AnyMatch = _AnyMatch()


@dataclass(slots=True)
class SnapshotEdit:
    """One pending source-file rewrite produced by ``snapshot(...)``."""

    file: Path
    call_line: int
    call_col: int
    new_value: Any


_PENDING: list[SnapshotEdit] = []


def pending_edits() -> list[SnapshotEdit]:
    return list(_PENDING)


class SnapshotValue:
    """Marker carrying a snapshot's recorded value + the source location.

    Returned by :func:`snapshot`. Instances participate in equality
    against an :class:`~causeway._testing.expect.Expectation` via
    :meth:`compare`; users do not normally call methods directly.
    """

    __slots__ = ("call_col", "call_line", "expected", "name", "source_file")

    def __init__(
        self,
        expected: Any,
        *,
        source_file: Path | None,
        call_line: int,
        call_col: int,
        name: str | None,
    ) -> None:
        self.expected = expected
        self.source_file = source_file
        self.call_line = call_line
        self.call_col = call_col
        self.name = name

    def compare(self, actual: Any, source_path: tuple[str, ...] = ()) -> None:
        reg = current_registry()
        update = bool(reg and reg.update_snapshots)
        if self.expected is _UNSET:
            if not update:
                raise ScenarioAssertionError(
                    message=(
                        "snapshot() has no recorded value yet — "
                        "rerun with `pytest --update-snapshots` to record"
                    ),
                    actual=actual,
                    path=source_path,
                )
            self._record(actual)
            return
        if not _matches(self.expected, actual):
            if update:
                self._record(actual)
                return
            raise ScenarioAssertionError(
                message="snapshot mismatch",
                expected=self.expected,
                actual=actual,
                path=source_path,
            )

    def _record(self, actual: Any) -> None:
        if self.source_file is None:
            return
        _PENDING.append(
            SnapshotEdit(
                file=self.source_file,
                call_line=self.call_line,
                call_col=self.call_col,
                new_value=actual,
            )
        )

    def __repr__(self) -> str:
        return f"snapshot({self.expected!r})"


def _matches(expected: Any, actual: Any) -> bool:
    """Structural equality with ``Ellipsis`` as a wildcard at any node."""
    if isinstance(expected, _AnyMatch) or expected is ...:
        return True
    if type(expected) is not type(actual):
        # Allow lists and tuples to interoperate (msgspec gives lists from json).
        if not (
            isinstance(expected, list | tuple) and isinstance(actual, list | tuple)
        ):
            return bool(expected == actual)
    if isinstance(expected, dict) and isinstance(actual, dict):
        if set(expected.keys()) != set(actual.keys()):
            return False
        return all(_matches(expected[k], actual[k]) for k in expected)
    if isinstance(expected, list | tuple) and isinstance(actual, list | tuple):
        if len(expected) != len(actual):
            return False
        return all(_matches(e, a) for e, a in zip(expected, actual, strict=True))
    return bool(expected == actual)


def snapshot(
    expected: Any = _UNSET,
    /,
    *,
    name: str | None = None,
) -> SnapshotValue:
    """Mark a value as a snapshot for inline-rewrite assertion.

    The literal ``snapshot(...)`` call's source line is captured from the
    caller's stack frame so the rewriter can patch it in place when
    ``--update-snapshots`` is used.
    """
    frame = inspect.currentframe()
    caller = frame.f_back if frame is not None else None
    src_file: Path | None = None
    line = 0
    col = 0
    if caller is not None:
        src_file = Path(caller.f_code.co_filename).resolve()
        line = caller.f_lineno
        # f_lasti points at the call instruction; column info isn't always
        # available, so leave col at 0 and let the rewriter locate by line.
    return SnapshotValue(
        expected,
        source_file=src_file,
        call_line=line,
        call_col=col,
        name=name,
    )
