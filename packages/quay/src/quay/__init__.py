"""Quay — a lean backend framework for type-safe Python APIs.

Public API surface for v0.1. Anything not listed in ``__all__`` (or imported
from a private underscore module like ``quay._methods``) is implementation
detail and may change in any release. See ``docs/semver.md``.

Slice landed in this release:

- File-based routing primitives — :func:`get` / :func:`post` / :func:`put` /
  :func:`patch` / :func:`delete` decorators, :func:`quay.routing.discover` and
  :func:`quay.routing.register` for the walker.
- Scopes — :func:`provide` for ``_scope.py`` providers.
- Middleware — :class:`Middleware` base class and :func:`guard` decorator.
- Config — :class:`Settings` (re-export of ``pydantic_settings.BaseSettings``)
  and :class:`Manifest` (parsed ``quay.toml``).

Re-exported from ``dyadpy`` so app code only depends on ``quay``:

- :func:`Depends` — DI marker for handler parameters.
- :func:`raises` — declare exception types the handler may raise (flows to
  the generated TS client's ``Result<T, E>`` union).
- :func:`stream` — SSE return type marker.
- :data:`Bytes` — raw-body sentinel.
"""

from __future__ import annotations

from dyadpy import Bytes, Depends, raises, stream

from quay._methods import delete, get, patch, post, put
from quay.config import Manifest, Settings
from quay.middleware import Middleware, guard
from quay.scope import provide

__version__ = "0.1.0a0"

__all__ = [
    "Bytes",
    "Depends",
    "Manifest",
    "Middleware",
    "Settings",
    "__version__",
    "delete",
    "get",
    "guard",
    "patch",
    "post",
    "provide",
    "put",
    "raises",
    "stream",
]
