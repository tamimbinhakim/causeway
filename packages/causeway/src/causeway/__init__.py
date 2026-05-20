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
from causeway.contracts import Webhooks, WebhookStore
from causeway.events import Event
from causeway.middleware import IdempotencyMiddleware, Middleware, MiddlewareItem, guard, use
from causeway.observability import RequestIdMiddleware, configure_logging, configure_otel
from causeway.pagination import Cursor, Paginated
from causeway.plugins import env, register
from causeway.scope import dependency, provide
from causeway.tasks import cron, task, tasks_eager
from causeway.webhooks import (
    IncomingWebhook,
    InMemoryWebhooks,
    InMemoryWebhookStore,
    Subscriber,
    WebhookDeliveryFailed,
    new_secret,
    sign_payload,
    verify,
    verify_signature,
)

__version__ = "0.3.8"

__all__ = [
    "BatchFailure",
    "BatchResult",
    "Bytes",
    "Cursor",
    "Depends",
    "Event",
    "IdempotencyMiddleware",
    "InMemoryWebhookStore",
    "InMemoryWebhooks",
    "IncomingWebhook",
    "Manifest",
    "Middleware",
    "MiddlewareItem",
    "Paginated",
    "RequestIdMiddleware",
    "Settings",
    "Subscriber",
    "WebhookDeliveryFailed",
    "WebhookStore",
    "Webhooks",
    "__version__",
    "batch",
    "check_permission",
    "configure_logging",
    "configure_otel",
    "create_app",
    "cron",
    "delete",
    "dependency",
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
    "use",
    "verify",
    "verify_signature",
]
