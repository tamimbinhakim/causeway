"""HTTP error types + ``application/problem+json`` renderer (RFC 9457).

Subclass :class:`HttpError` to add typed errors that flow to the
generated TS client as a discriminated union (via ``@raises(...)``).
Anything that isn't an :class:`HttpError` becomes a generic 500 — the
original exception is kept off the wire so internal types don't leak.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Mapping
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

    def to_dict(
        self,
        *,
        request: Request | None = None,
        error_formatter: HttpErrorFormatter | None = None,
    ) -> dict[str, Any]:
        """Payload used by ``@raises`` result envelopes."""
        return format_http_error(self, request=request, error_formatter=error_formatter)


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


HttpErrorFormatter = Callable[[HttpError, Request | None], Mapping[str, Any]]
ErrorRenderer = Callable[[Request, Exception], Awaitable[Response]]


def format_http_error(
    exc: HttpError,
    *,
    request: Request | None = None,
    error_formatter: HttpErrorFormatter | None = None,
) -> dict[str, Any]:
    """Return the canonical wire payload for a typed HTTP error."""
    raw = dict(error_formatter(exc, request)) if error_formatter is not None else {}

    raw.setdefault("status", exc.status)
    raw.setdefault("code", exc.code)
    raw.setdefault("message", exc.message)
    raw.setdefault("detail", exc.detail)
    return raw


def render_problem(
    exc: BaseException,
    *,
    request_id: str | None = None,
    request: Request | None = None,
    error_formatter: HttpErrorFormatter | None = None,
) -> Response:
    """Turn an exception into an ``application/problem+json`` response."""
    if isinstance(exc, HttpError):
        payload = format_http_error(exc, request=request, error_formatter=error_formatter)
        status = int(payload["status"])
        body: dict[str, Any] = {
            "type": f"about:blank#{payload['code']}",
            "title": payload["code"],
            "status": status,
            "detail": payload["message"],
        }
        if payload["detail"]:
            body["params"] = payload["detail"]
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


def make_error_renderer(error_formatter: HttpErrorFormatter | None = None) -> ErrorRenderer:
    """Build a Starlette exception renderer with optional ``HttpError`` formatting."""

    async def renderer(request: Request, exc: Exception) -> Response:
        request_id = getattr(request.state, "request_id", None)
        if not isinstance(exc, (HttpError, PermissionError, LookupError)):
            log_exception(
                _log,
                exc,
                request=request,
                request_id=request_id if isinstance(request_id, str) else None,
            )
        return render_problem(
            exc,
            request_id=request_id if isinstance(request_id, str) else None,
            request=request,
            error_formatter=error_formatter,
        )

    return renderer


async def error_renderer(request: Request, exc: Exception) -> Response:
    """Starlette ``exception_handlers`` entry. Reads ``request.state.request_id`` if set."""
    return await make_error_renderer()(request, exc)


__all__ = [
    "BadRequest",
    "Conflict",
    "ErrorRenderer",
    "Forbidden",
    "HttpError",
    "HttpErrorFormatter",
    "Internal",
    "NotFound",
    "TooManyRequests",
    "Unauthorized",
    "error_renderer",
    "format_http_error",
    "make_error_renderer",
    "render_problem",
]
