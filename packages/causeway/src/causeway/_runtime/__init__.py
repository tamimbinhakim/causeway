"""Causeway's RPC runtime — the type-safe Python↔TypeScript substrate.

Private (underscore-prefixed) by convention: causeway's top-level package
re-exports the bits app code needs (``App``, ``Context``, ``Depends``,
``stream``, ``raises``, ``bidi``, ``Form``, ``Bytes``). Reach into this
module only when you're writing framework extensions that need to talk to
the runtime directly.

``causeway._runtime.tasks`` is loaded lazily via PEP 562 — it pulls in
asyncio internals that only matter when you actually queue a background
job. Bidi stays on the default path (cheap to import).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from causeway._runtime.app import App
from causeway._runtime.bidi import BidiChannel, bidi
from causeway._runtime.context import Context, Depends, after
from causeway._runtime.errors import raises
from causeway._runtime.params import Form
from causeway._runtime.streaming import SsePayload, stream

if TYPE_CHECKING:  # pragma: no cover — re-export shape only
    from causeway._runtime.tasks import (
        InMemoryBackend,
        TaskBackend,
        TaskState,
        mount_task_routes,
    )

# Raw-body sentinel: annotate a handler param or return with ``Bytes`` to
# skip the JSON envelope entirely. Identical to the ``bytes`` builtin; the
# alias is exported for documentation and explicit-intent reasons.
Bytes = bytes

_LAZY_TASKS = {"InMemoryBackend", "TaskBackend", "TaskState", "mount_task_routes"}


def __getattr__(name: str) -> Any:
    if name in _LAZY_TASKS:
        import importlib

        return getattr(importlib.import_module("causeway._runtime.tasks"), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "App",
    "BidiChannel",
    "Bytes",
    "Context",
    "Depends",
    "Form",
    "InMemoryBackend",
    "SsePayload",
    "TaskBackend",
    "TaskState",
    "after",
    "bidi",
    "mount_task_routes",
    "raises",
    "stream",
]
