"""Causeway — a lean backend framework for type-safe Python APIs.

Public API surface for v0.1. Anything not listed in ``__all__`` (or imported
from a private underscore module like ``causeway._methods``) is implementation
detail and may change in any release. See ``docs/stability/semver.md``.

Slice landed in this release:

- File-based routing primitives — :func:`get` / :func:`post` / :func:`put` /
  :func:`patch` / :func:`delete` decorators, :func:`causeway.routing.discover` and
  :func:`causeway.routing.register` for the walker.
- Scopes — :func:`provide` for ``_scope.py`` providers.
- Middleware — :class:`Middleware` base class and :func:`guard` decorator.
- Config — :class:`Settings` (re-export of ``pydantic_settings.BaseSettings``)
  and :class:`Manifest` (parsed ``causeway.toml``).

Re-exported from ``dyadpy`` so app code only depends on ``causeway``:

- :func:`Depends` — DI marker for handler parameters.
- :func:`raises` — declare exception types the handler may raise (flows to
  the generated TS client's ``Result<T, E>`` union).
- :func:`stream` — SSE return type marker.
- :data:`Bytes` — raw-body sentinel.
"""

from __future__ import annotations

from dyadpy import Bytes, Depends, raises, stream

from causeway import errors
from causeway._methods import delete, get, patch, post, put
from causeway.app import create_app
from causeway.config import Manifest, Settings
from causeway.middleware import Middleware, guard
from causeway.observability import RequestIdMiddleware, configure_logging, configure_otel
from causeway.plugins import env, register
from causeway.scope import provide
from causeway.tasks import cron, task, tasks_eager

__version__ = "0.1.0"

__all__ = [
    "Bytes",
    "Depends",
    "Manifest",
    "Middleware",
    "RequestIdMiddleware",
    "Settings",
    "__version__",
    "configure_logging",
    "configure_otel",
    "create_app",
    "cron",
    "delete",
    "env",
    "errors",
    "get",
    "guard",
    "patch",
    "post",
    "provide",
    "put",
    "raises",
    "register",
    "stream",
    "task",
    "tasks_eager",
]
