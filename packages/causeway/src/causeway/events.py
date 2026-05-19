"""Typed events.

The ``Event`` class is the canonical handle for everything related to one
event: payload schema, wire name, in-process listeners, and (when
``webhook=True``) outbound webhook delivery. Subclasses register themselves
at import via ``__init_subclass__``; the framework walks ``app/events/``
and ``app/listeners/`` at boot to discover them.

Naming convention is flat + underscored:

- File ``app/events/customer_created.py``
- Class ``CustomerCreated`` (canonical Python identity)
- Wire name ``"customer.created"`` (PascalCase split on case boundaries → dot.lowercase)

The class is the bus for itself: ``CustomerCreated._listeners`` and
``CustomerCreated._subscribers`` hold the fan-out targets. There's no
separate plugin point at the event-bus layer — durable buses live downstream
through the task adapter.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import msgspec

from causeway._loader import import_path

if TYPE_CHECKING:
    pass

_log = logging.getLogger("causeway.events")

# Process-wide registry of every declared Event subclass, keyed by wire_name.
_events: dict[str, type[Event]] = {}


Listener = Callable[[Any], Awaitable[None]]


@dataclass(slots=True)
class EmitResult:
    """Returned from ``Event.emit()``. Lists the webhook delivery task ids
    scheduled for outbound subscribers (empty when ``webhook=False`` or no
    subscribers matched)."""

    delivery_ids: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Wire-name derivation
# ---------------------------------------------------------------------------

# Splits PascalCase into pieces at every transition from lowercase/digit →
# uppercase, and at every run of capitals followed by a lowercase (so
# ``HTTPRequestFailed`` → ``HTTP``, ``Request``, ``Failed``).
_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def _pascal_to_dotted(name: str) -> str:
    """``CustomerCreated`` → ``customer.created``.

    Capital runs collapse into one token until the next lowercase start, so
    ``HTTPRequestFailed`` → ``http.request.failed`` (same as
    ``HttpRequestFailed``). Apps shouldn't declare both variants since they
    would produce the same wire name and collide at registration.
    """
    parts = _BOUNDARY.split(name)
    return ".".join(p.lower() for p in parts)


def _pascal_to_snake(name: str) -> str:
    """``CustomerCreated`` → ``customer_created``. Used for filename validation."""
    return _pascal_to_dotted(name).replace(".", "_")


# ---------------------------------------------------------------------------
# Event base class
# ---------------------------------------------------------------------------


class Event(msgspec.Struct, kw_only=True):
    """Base class for every typed event.

    Subclasses look like::

        class CustomerCreated(Event):
            webhook = True  # opt into outbound webhook fan-out
            organization_id: UUID
            id: UUID
            email: str

    The class is registered globally by ``wire_name`` at import time. The
    file path is purely organizational — the class name is canonical.

    ``webhook`` is a plain class attribute, not a field (no annotation), so
    msgspec doesn't pick it up as part of the payload schema. Subclasses
    that omit it inherit ``False`` from this base.
    """

    # ``webhook`` is intentionally NOT annotated — msgspec.Struct treats
    # annotated class-level definitions as fields. Plain attributes pass
    # through. We declare ``wire_name`` etc. with ClassVar so subclass
    # registration can write to them without msgspec field-detecting them.
    webhook = False
    wire_name: ClassVar[str]
    _listeners: ClassVar[list[Listener]]
    _subscribers: ClassVar[list[Any]]  # webhooks.Subscriber, late-imported

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.wire_name = _pascal_to_dotted(cls.__name__)
        cls._listeners = []
        cls._subscribers = []
        # cls.webhook is either inherited (False) or set on the subclass.

        existing = _events.get(cls.wire_name)
        if existing is not None and existing is not cls:
            msg = (
                f"event wire-name collision: {cls.__qualname__} and "
                f"{existing.__qualname__} both produce {cls.wire_name!r}"
            )
            raise RuntimeError(msg)
        _events[cls.wire_name] = cls

    # -- Listener registration ------------------------------------------------

    @classmethod
    def listen(cls, fn: Listener) -> Listener:
        """Decorator that registers ``fn`` as an in-process listener.

        Validates at decoration time that ``fn`` is async and takes one
        positional parameter (we don't enforce the annotation to match the
        class — Python doesn't reliably resolve forward references here, and
        a static checker is the right place to catch that mismatch).
        """
        if not inspect.iscoroutinefunction(fn):
            msg = f"@{cls.__name__}.listen requires an async function; got {fn!r}"
            raise TypeError(msg)
        sig = inspect.signature(fn)
        params = [p for p in sig.parameters.values() if p.kind != p.VAR_KEYWORD]
        if len(params) != 1:
            msg = (
                f"@{cls.__name__}.listen requires exactly one parameter; "
                f"{fn.__qualname__} takes {len(params)}"
            )
            raise TypeError(msg)
        cls._listeners.append(fn)
        return fn

    # -- Emit -----------------------------------------------------------------

    async def emit(self) -> EmitResult:
        """Fan out this instance.

        Runs every in-process listener concurrently (raising the first
        failure); then, when ``webhook=True``, schedules one delivery task
        per matching subscriber. Listeners are awaited; deliveries are not —
        callers never block on outbound HTTP.
        """
        cls = type(self)

        if cls._listeners:
            await asyncio.gather(*(fn(self) for fn in cls._listeners))

        delivery_ids: list[str] = []
        if cls.webhook:
            delivery_ids = await _fanout_webhooks(self)

        return EmitResult(delivery_ids=delivery_ids)


# ---------------------------------------------------------------------------
# Webhook fan-out hook (filled in by causeway.webhooks at import)
# ---------------------------------------------------------------------------

_fanout_impl: Callable[[Event], Awaitable[list[str]]] | None = None


def _set_fanout(impl: Callable[[Event], Awaitable[list[str]]]) -> None:
    """``causeway.webhooks`` calls this on import to wire its fan-out logic
    into ``Event.emit()``. Keeping the dependency one-way avoids an import
    cycle between events and webhooks."""
    global _fanout_impl
    _fanout_impl = impl


async def _fanout_webhooks(event: Event) -> list[str]:
    if _fanout_impl is None:
        # Webhooks module never imported — nothing to fan out to.
        return []
    return await _fanout_impl(event)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Discovered:
    """Snapshot returned by :func:`discover`."""

    events: dict[str, type[Event]] = field(default_factory=dict)
    listener_modules: list[Path] = field(default_factory=list)


def discover(
    events_root: str | Path,
    listeners_root: str | Path | None = None,
) -> Discovered:
    """Walk ``events_root`` (and optional ``listeners_root``), importing every
    ``.py`` file so that ``Event`` subclasses register themselves and
    ``@<Event>.listen`` decorators run.

    Returns a snapshot of every event class seen, plus the listener modules
    imported. The global ``_events`` registry is the source of truth at
    runtime — the snapshot is for diagnostics and testing.
    """
    root = Path(events_root)
    if not root.is_dir():
        msg = f"events root not found: {root}"
        raise FileNotFoundError(msg)

    out = Discovered()
    _walk_events(root, out)

    if listeners_root is not None:
        l_root = Path(listeners_root)
        if l_root.is_dir():
            _walk_listeners(l_root, out)

    return out


def _walk_events(events_root: Path, out: Discovered) -> None:
    for entry in sorted(events_root.iterdir(), key=lambda p: p.name):
        if entry.name.startswith(".") or entry.name.startswith("_"):
            continue
        if entry.is_dir():
            # Folders inside events/ are not the convention; skip to keep
            # discovery predictable.
            continue
        if entry.suffix != ".py":
            continue
        _load_event_file(entry, out)


def _load_event_file(file: Path, out: Discovered) -> None:
    mod = import_path(file, label_prefix="_causeway_events")
    expected_stem = file.stem  # e.g. "customer_created"

    found_classes: list[type[Event]] = []
    for attr in dir(mod):
        if attr.startswith("_"):
            continue
        obj = getattr(mod, attr)
        if not isinstance(obj, type) or not issubclass(obj, Event) or obj is Event:
            continue
        # Only count classes actually defined in this module — re-exports get
        # discovered through their original file, not here.
        if getattr(obj, "__module__", None) != getattr(mod, "__name__", None):
            continue
        found_classes.append(obj)

    if not found_classes:
        return

    if len(found_classes) > 1:
        names = ", ".join(c.__name__ for c in found_classes)
        msg = (
            f"{file} declares multiple Event subclasses ({names}); convention is one event per file"
        )
        raise RuntimeError(msg)

    cls = found_classes[0]
    expected_filename = _pascal_to_snake(cls.__name__)
    if expected_filename != expected_stem:
        msg = (
            f"event filename mismatch: {file.name} declares class "
            f"{cls.__name__}, expected file named {expected_filename}.py"
        )
        raise RuntimeError(msg)

    out.events[cls.wire_name] = cls


def _walk_listeners(listeners_root: Path, out: Discovered) -> None:
    root = listeners_root.resolve()
    for entry in sorted(listeners_root.rglob("*.py")):
        rel = entry.resolve().relative_to(root)
        # Only filter components under the listeners root — the absolute
        # path may contain ``_``/``.`` segments (``/private/var/folders/_c/…``).
        if any(p.startswith("_") or p.startswith(".") for p in rel.parts):
            continue
        # Importing the module runs every ``@<Event>.listen`` decorator at
        # its module scope, which is what wires listeners up.
        import_path(entry, label_prefix="_causeway_listeners")
        out.listener_modules.append(entry)


# ---------------------------------------------------------------------------
# Testing / introspection helpers
# ---------------------------------------------------------------------------


def all_events() -> dict[str, type[Event]]:
    """Return a snapshot of every registered ``Event`` subclass."""
    return dict(_events)


def webhookable_events() -> list[type[Event]]:
    """Every ``Event`` subclass with ``webhook = True``. Useful for
    populating a subscription-management UI's event picker."""
    return [cls for cls in _events.values() if cls.webhook]


def _reset_registry() -> None:
    """For tests. Drops every registered event class and clears their
    listeners + subscribers. Call between tests that declare events locally
    so leftover state doesn't bleed across cases."""
    for cls in list(_events.values()):
        cls._listeners.clear()
        cls._subscribers.clear()
    _events.clear()


__all__ = [
    "Discovered",
    "EmitResult",
    "Event",
    "Listener",
    "all_events",
    "discover",
    "webhookable_events",
]
