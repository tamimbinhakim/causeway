from __future__ import annotations

import asyncio
import inspect
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

import msgspec

from causeway._loader import import_path

_log = logging.getLogger("causeway.events")
_events: dict[str, type[Event]] = {}
_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")

Listener = Callable[[Any], Awaitable[None]]


@dataclass(slots=True)
class EmitResult:
    delivery_ids: list[str] = field(default_factory=list)


def _pascal_to_dotted(name: str) -> str:
    return ".".join(part.lower() for part in _BOUNDARY.split(name))


def _pascal_to_snake(name: str) -> str:
    return _pascal_to_dotted(name).replace(".", "_")


class Event(msgspec.Struct, kw_only=True):
    webhook = False
    wire_name: ClassVar[str]
    _listeners: ClassVar[list[Listener]]
    _subscribers: ClassVar[list[Any]]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.wire_name = _pascal_to_dotted(cls.__name__)
        cls._listeners = []
        cls._subscribers = []

        existing = _events.get(cls.wire_name)
        if existing is not None and existing is not cls:
            msg = (
                f"event wire-name collision: {cls.__qualname__} and "
                f"{existing.__qualname__} both produce {cls.wire_name!r}"
            )
            raise RuntimeError(msg)
        _events[cls.wire_name] = cls

    @classmethod
    def listen(cls, fn: Listener) -> Listener:
        if not inspect.iscoroutinefunction(fn):
            msg = f"@{cls.__name__}.listen requires an async function; got {fn!r}"
            raise TypeError(msg)

        params = [p for p in inspect.signature(fn).parameters.values() if p.kind != p.VAR_KEYWORD]
        if len(params) != 1:
            msg = (
                f"@{cls.__name__}.listen requires exactly one parameter; "
                f"{fn.__qualname__} takes {len(params)}"
            )
            raise TypeError(msg)

        cls._listeners.append(fn)
        return fn

    async def emit(self) -> EmitResult:
        cls = type(self)
        if cls._listeners:
            await asyncio.gather(*(fn(self) for fn in cls._listeners))
        return EmitResult(delivery_ids=await _fanout_webhooks(self) if cls.webhook else [])


_fanout_impl: Callable[[Event], Awaitable[list[str]]] | None = None


def _set_fanout(impl: Callable[[Event], Awaitable[list[str]]]) -> None:
    global _fanout_impl
    _fanout_impl = impl


async def _fanout_webhooks(event: Event) -> list[str]:
    if _fanout_impl is None:
        return []
    return await _fanout_impl(event)


@dataclass(slots=True)
class Discovered:
    events: dict[str, type[Event]] = field(default_factory=dict)
    listener_modules: list[Path] = field(default_factory=list)


def discover(
    events_root: str | Path,
    listeners_root: str | Path | None = None,
) -> Discovered:
    root = Path(events_root)
    if not root.is_dir():
        msg = f"events root not found: {root}"
        raise FileNotFoundError(msg)

    out = Discovered()
    for file in _visible_py_files(root):
        _load_event_file(file, out)

    if listeners_root is not None and Path(listeners_root).is_dir():
        _walk_listeners(Path(listeners_root), out)

    return out


def _load_event_file(file: Path, out: Discovered) -> None:
    mod = import_path(file, label_prefix="_causeway_events")
    found: list[type[Event]] = []
    for attr in dir(mod):
        if attr.startswith("_"):
            continue
        obj = getattr(mod, attr)
        if not isinstance(obj, type) or not issubclass(obj, Event) or obj is Event:
            continue
        if getattr(obj, "__module__", None) == getattr(mod, "__name__", None):
            found.append(obj)

    if not found:
        return

    if len(found) > 1:
        names = ", ".join(c.__name__ for c in found)
        msg = (
            f"{file} declares multiple Event subclasses ({names}); convention is one event per file"
        )
        raise RuntimeError(msg)

    cls = found[0]
    expected = _pascal_to_snake(cls.__name__)
    if expected != file.stem:
        msg = (
            f"event filename mismatch: {file.name} declares class "
            f"{cls.__name__}, expected file named {expected}.py"
        )
        raise RuntimeError(msg)

    out.events[cls.wire_name] = cls


def _walk_listeners(listeners_root: Path, out: Discovered) -> None:
    for entry in _visible_py_tree(listeners_root):
        import_path(entry, label_prefix="_causeway_listeners")
        out.listener_modules.append(entry)


def _visible_py_files(root: Path) -> list[Path]:
    return [
        entry
        for entry in sorted(root.iterdir(), key=lambda p: p.name)
        if entry.is_file() and entry.suffix == ".py" and not entry.name.startswith(("_", "."))
    ]


def _visible_py_tree(root: Path) -> list[Path]:
    resolved = root.resolve()
    return [
        entry
        for entry in sorted(root.rglob("*.py"))
        if not any(p.startswith(("_", ".")) for p in entry.resolve().relative_to(resolved).parts)
    ]


def all_events() -> dict[str, type[Event]]:
    return dict(_events)


def webhookable_events() -> list[type[Event]]:
    return [cls for cls in _events.values() if cls.webhook]


def _reset_registry() -> None:
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
