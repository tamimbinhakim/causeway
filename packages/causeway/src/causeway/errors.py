"""HTTP error types + ``application/problem+json`` renderer (RFC 9457).

Subclass :class:`HttpError` to add typed errors that flow to the
generated TS client as a discriminated union (via ``@raises(...)``).
Anything that isn't an :class:`HttpError` becomes a generic 500 — the
original exception is kept off the wire so internal types don't leak.
"""

from __future__ import annotations

import logging
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from causeway._traceback import log_exception

_log = logging.getLogger("causeway.errors")


class HttpError(Exception):
    """Base class for typed HTTP errors. Subclass to add new ones."""

    status: int = 500
    code: str = "internal"
    message: str
    detail: dict[str, Any]

    def __init__(self, message: str | None = None, *, detail: dict[str, Any] | None = None) -> None:
        super().__init__(message or self.code)
        self.message = message or self.code
        self.detail = detail or {}
        self.__suppress_context__ = True


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
    if request_id is not None:
        body["request_id"] = request_id
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


async def error_renderer(request: Request, exc: Exception) -> Response:
    """Starlette ``exception_handlers`` entry. Reads ``request.state.request_id`` if set."""
    request_id = getattr(request.state, "request_id", None)
    if not isinstance(exc, (HttpError, PermissionError, LookupError)):
        log_exception(
            _log,
            exc,
            request=request,
            request_id=request_id if isinstance(request_id, str) else None,
        )
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
