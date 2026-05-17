"""Per-module scenario registry, addressed by a contextvar.

The pytest plugin sets up a :class:`Registry` before importing a route
file so :func:`scenario` can record itself into it. Outside the plugin
(production imports) the contextvar is unset and ``scenario`` is a
no-op — that's what keeps the ``if __name__ == "__causeway_test__":``
block free at runtime.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from causeway._testing.scenario import ScenarioBody


@dataclass(slots=True)
class RegisteredScenario:
    """Captured by :func:`scenario` during collection."""

    label: str
    body: ScenarioBody
    lineno: int


@dataclass(slots=True)
class Registry:
    """Holds every scenario discovered in a single route file."""

    route_file: Path
    routes_root: Path
    mode: str = "collect"  # "collect" or "execute"
    target_index: int | None = None  # in execute mode, run only this index
    target_label: str | None = None
    scenarios: list[RegisteredScenario] = field(default_factory=list)
    update_snapshots: bool = False


_REGISTRY_VAR: ContextVar[Registry | None] = ContextVar("_causeway_registry", default=None)


def set_registry(registry: Registry | None) -> None:
    _REGISTRY_VAR.set(registry)


def current_registry() -> Registry | None:
    return _REGISTRY_VAR.get()
