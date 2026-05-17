"""Causeway — a lean backend framework for type-safe Python APIs.

Public API surface. Anything not listed in ``__all__`` (or imported from a
private underscore module like ``causeway._methods``) is implementation
detail and may change in any release. See ``docs/stability/semver.md`` and
``CHANGELOG.md``.

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
from causeway.auth import check_permission, expand_permissions, require_permission
from causeway.batch import BatchFailure, BatchResult, batch
from causeway.config import Manifest, Settings
from causeway.middleware import IdempotencyMiddleware, Middleware, guard
from causeway.observability import RequestIdMiddleware, configure_logging, configure_otel
from causeway.pagination import Cursor, Paginated
from causeway.plugins import env, register
from causeway.scope import provide
from causeway.tasks import cron, task, tasks_eager
from causeway.webhooks import (
    InMemoryWebhooks,
    new_secret,
    sign_payload,
    verify_signature,
)

__version__ = "0.1.1"

__all__ = [
    "BatchFailure",
    "BatchResult",
    "Bytes",
    "Cursor",
    "Depends",
    "IdempotencyMiddleware",
    "InMemoryWebhooks",
    "Manifest",
    "Middleware",
    "Paginated",
    "RequestIdMiddleware",
    "Settings",
    "__version__",
    "batch",
    "check_permission",
    "configure_logging",
    "configure_otel",
    "create_app",
    "cron",
    "delete",
    "env",
    "errors",
    "expand_permissions",
    "get",
    "guard",
    "new_secret",
    "patch",
    "post",
    "provide",
    "put",
    "raises",
    "register",
    "require_permission",
    "sign_payload",
    "stream",
    "task",
    "tasks_eager",
    "verify_signature",
]
