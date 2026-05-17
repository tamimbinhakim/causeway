"""Assertion error carrying scenario context and a rendered diff."""

from __future__ import annotations

import difflib
import pprint
from pathlib import Path
from typing import Any

_UNSET: Any = object()


class ScenarioAssertionError(AssertionError):
    """Failure raised by ``expect(...)`` and ``snapshot(...)`` comparisons.

    Carries enough context (route file, scenario label, json path) that
    pytest's ``-v`` output identifies *where* the assertion fired even
    though the route file isn't an assertion-rewritten test module.
    """

    def __init__(
        self,
        *,
        message: str,
        actual: Any = _UNSET,
        expected: Any = _UNSET,
        path: tuple[str, ...] = (),
        route_file: Path | None = None,
        scenario_label: str | None = None,
    ) -> None:
        self.message = message
        self.actual = actual
        self.expected = expected
        self.path = path
        self.route_file = route_file
        self.scenario_label = scenario_label
        super().__init__(self._render())

    def _render(self) -> str:
        parts: list[str] = [self.message]
        if self.scenario_label and self.route_file:
            parts.append(f"  in {self.route_file}::{self.scenario_label}")
        elif self.route_file:
            parts.append(f"  in {self.route_file}")
        if self.path:
            parts.append(f"  at .{'.'.join(self.path)}")
        if self.actual is not _UNSET and self.expected is not _UNSET:
            parts.append(_diff(self.expected, self.actual))
        return "\n".join(parts)


def _diff(expected: Any, actual: Any) -> str:
    e = pprint.pformat(expected, width=80, sort_dicts=True).splitlines()
    a = pprint.pformat(actual, width=80, sort_dicts=True).splitlines()
    return "\n".join(difflib.unified_diff(e, a, fromfile="expected", tofile="actual", lineterm=""))
