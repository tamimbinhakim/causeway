"""Quay's error types + problem+json renderer.

Quay's own error classes mirror the common HTTP error shape so handlers
declare them via ``@raises(NotFound)`` and the generated TS client gets a
discriminated union. The base class :class:`HttpError` carries the status
code, a stable ``code`` string, and an optional ``detail`` map; the
renderer turns it into ``application/problem+json`` per RFC 9457.

Anything not subclassing :class:`HttpError` becomes a 500 with a generic
``"internal"`` code in the rendered body — the original exception class
is kept off the wire by default so internal types don't leak.
"""

from __future__ import annotations

import logging
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_log = logging.getLogger("quay.errors")


class HttpError(Exception):
    """Base class for typed HTTP errors. Subclass to add new ones."""

    status: int = 500
    code: str = "internal"

    def __init__(self, message: str | None = None, *, detail: dict[str, Any] | None = None) -> None:
        super().__init__(message or self.code)
        self.message = message or self.code
        self.detail = detail or {}


class BadRequest(HttpError):
    status = 400
    code = "bad_request"


class Unauthorized(HttpError):
    status = 401
    code = "unauthorized"


class Forbidden(HttpError):
    status = 403
    code = "forbidden"


class NotFound(HttpError):
    status = 404
    code = "not_found"


class Conflict(HttpError):
    status = 409
    code = "conflict"


class TooManyRequests(HttpError):
    status = 429
    code = "too_many_requests"


class Internal(HttpError):
    status = 500
    code = "internal"


def render_problem(exc: BaseException, *, request_id: str | None = None) -> Response:
    """Turn an exception into an ``application/problem+json`` response."""
    if isinstance(exc, HttpError):
        body: dict[str, Any] = {
            "type": f"about:blank#{exc.code}",
            "title": exc.code,
            "status": exc.status,
            "detail": exc.message,
        }
        if exc.detail:
            body["params"] = exc.detail
        status = exc.status
    elif isinstance(exc, PermissionError):
        body = {
            "type": "about:blank#forbidden",
            "title": "forbidden",
            "status": 403,
            "detail": str(exc) or "permission denied",
        }
        status = 403
    elif isinstance(exc, LookupError):
        body = {
            "type": "about:blank#not_found",
            "title": "not_found",
            "status": 404,
            "detail": str(exc) or "not found",
        }
        status = 404
    else:
        # Never surface the raw exception message — it may contain secrets,
        # stack frames, or SQL. Subclass ``HttpError`` to opt into a custom one.
        body = {
            "type": "about:blank#internal",
            "title": "internal",
            "status": 500,
            "detail": "internal server error",
        }
        status = 500
        _log.exception("unhandled exception", exc_info=exc)
    if request_id is not None:
        body["request_id"] = request_id
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


async def error_renderer(request: Request, exc: Exception) -> Response:
    """Starlette ``exception_handlers`` entry. Pulls the request id off
    ``request.state.request_id`` if the request-id middleware set one.
    """
    request_id = getattr(request.state, "request_id", None)
    return render_problem(exc, request_id=request_id)


__all__ = [
    "BadRequest",
    "Conflict",
    "Forbidden",
    "HttpError",
    "Internal",
    "NotFound",
    "TooManyRequests",
    "Unauthorized",
    "error_renderer",
    "render_problem",
]
