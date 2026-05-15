"""Middleware base class + ``@guard`` decorator.

The ``_middleware.py`` convention is: each such file exports a ``middleware``
list. Items in the list are either:

- A ``Middleware`` instance (class with an ``async __call__(self, req, call_next)`` method).
- A function decorated with ``@guard`` (lightweight assertion that runs before the handler).

Composition order is enforced by ``quay.routing``: app-level → root → ... → leaf
on the way in; reverse on the way out.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable

from starlette.requests import Request as Request
from starlette.responses import Response as Response

CallNext = Callable[[Request], Awaitable[Response]]
GuardFn = Callable[[Request], Awaitable[None]]


@runtime_checkable
class Middleware(Protocol):
    """Per-subtree middleware. Subclass and implement ``__call__``."""

    async def __call__(self, req: Request, call_next: CallNext) -> Response: ...


def guard(fn: GuardFn) -> GuardFn:
    """Mark a function as a lightweight guard.

    Guards run before the handler. Raise an exception to short-circuit the
    request (a ``PermissionError`` becomes a 403; a ``LookupError`` becomes
    a 404; everything else lands in the error renderer).

    >>> @guard
    >>> async def require_admin(req):
    ...     user = await current_user(req)
    ...     if not user or not user.is_admin:
    ...         raise PermissionError("admin only")
    """
    fn.__quay_guard__ = True  # type: ignore[attr-defined]
    return fn


def is_guard(obj: Any) -> bool:
    return bool(getattr(obj, "__quay_guard__", False))


__all__ = ["CallNext", "GuardFn", "Middleware", "Request", "Response", "guard", "is_guard"]
