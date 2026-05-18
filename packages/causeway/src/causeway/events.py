"""In-process event dispatching.

File-based, like routes. Drop ``customer.create.py`` in ``app/events/`` and
every module-level ``async def`` in it becomes a listener for the
``customer:create`` event. Emit with :func:`emit` and the active
:class:`~causeway.contracts.EventBus` fans out concurrently.

Naming: ``foo.bar.py`` → ``foo:bar``; ``foo/bar.py`` → ``foo:bar`` (folders
are leading segments). Both forms can coexist; listeners for the same event
name merge across files. ``_``-prefixed files and directories are skipped.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from causeway._loader import import_path

_log = logging.getLogger("causeway.events")

Listener = Callable[[Any], Awaitable[None]]


@dataclass(slots=True)
class DiscoveredEvent:
    """All listeners for a single event name."""

    name: str
    listeners: list[Listener] = field(default_factory=list)
    sources: list[Path] = field(default_factory=list)


@dataclass(slots=True)
class Discovered:
    """Snapshot returned by :func:`discover`."""

    events: dict[str, DiscoveredEvent] = field(default_factory=dict)


def discover(events_root: str | Path) -> Discovered:
    """Walk ``events_root`` and return everything found.

    Pure: returns a snapshot without installing it on any bus. Call
    :func:`register` to bind the snapshot to the active bus.
    """
    root = Path(events_root)
    if not root.is_dir():
        msg = f"events root not found: {root}"
        raise FileNotFoundError(msg)

    out = Discovered()
    _walk(root, root, (), out)
    return out


def _walk(
    events_root: Path,
    cur: Path,
    prefix: tuple[str, ...],
    out: Discovered,
) -> None:
    for entry in sorted(cur.iterdir(), key=lambda p: p.name):
        if entry.name.startswith(".") or entry.name.startswith("_"):
            continue
        if entry.is_dir():
            _walk(events_root, entry, (*prefix, entry.name), out)
            continue
        if entry.suffix != ".py":
            continue
        _load_event_file(entry, prefix, out)


def _load_event_file(
    file: Path,
    prefix: tuple[str, ...],
    out: Discovered,
) -> None:
    stem_parts = tuple(file.stem.split("."))
    name = ":".join((*prefix, *stem_parts))
    mod = import_path(file, label_prefix="_causeway_events")

    event = out.events.get(name)
    if event is None:
        event = DiscoveredEvent(name=name)
        out.events[name] = event

    for attr in dir(mod):
        if attr.startswith("_"):
            continue
        obj = getattr(mod, attr)
        if not inspect.iscoroutinefunction(obj):
            continue
        # Skip re-exports: only count functions defined in this file.
        if getattr(obj, "__module__", None) != getattr(mod, "__name__", None):
            continue
        event.listeners.append(obj)

    event.sources.append(file)


_bus_var: ContextVar[Any] = ContextVar("_causeway_event_bus")


def set_bus(bus: Any) -> None:
    """Install the default event bus the rest of the process will use."""
    _bus_var.set(bus)


def _active_bus() -> Any:
    try:
        return _bus_var.get()
    except LookupError as exc:
        msg = (
            "No EventBus registered. Call causeway.events.set_bus(...) at boot, "
            "or rely on causeway.create_app which installs InMemoryEventBus by default."
        )
        raise RuntimeError(msg) from exc


def register(found: Discovered) -> None:
    """Install ``found`` onto the active bus so :func:`emit` can resolve names."""
    bus = _active_bus()
    install = getattr(bus, "install", None)
    if install is None:
        msg = f"{type(bus).__name__} does not accept discovered listeners (missing install)"
        raise TypeError(msg)
    install(found)


async def emit(name: str, payload: Any = None) -> None:
    """Dispatch ``name`` with ``payload`` through the active bus.

    Listeners run concurrently. The first failure raises out of :func:`emit`;
    remaining listeners' completion is not awaited.
    """
    await _active_bus().emit(name, payload)


class InMemoryEventBus:
    """Reference event bus. Fans out via :func:`asyncio.gather`."""

    contract_version: ClassVar[str] = "v1.0"

    def __init__(self) -> None:
        self._events: dict[str, DiscoveredEvent] = {}
        self._warned: set[str] = set()

    def install(self, found: Discovered) -> None:
        self._events = dict(found.events)

    async def startup(self, settings: Any) -> None:
        del settings  # Plugin contract; bus has no settings to consume.
        set_bus(self)

    async def shutdown(self) -> None:
        self._events.clear()
        self._warned.clear()

    async def ready(self) -> bool:
        return True

    async def emit(self, name: str, payload: Any) -> None:
        event = self._events.get(name)
        if event is None or not event.listeners:
            if name not in self._warned:
                _log.debug("no listeners for event %r", name)
                self._warned.add(name)
            return
        await asyncio.gather(*(listener(payload) for listener in event.listeners))


__all__ = [
    "Discovered",
    "DiscoveredEvent",
    "InMemoryEventBus",
    "Listener",
    "discover",
    "emit",
    "register",
    "set_bus",
]
