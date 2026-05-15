"""Bare ``@get`` / ``@post`` / etc. decorators.

Handlers in route files use the bare decorator; the file router (``causeway.routing``)
derives the URL path from the file location and registers the handler on the
underlying ``dyadpy.App``. The decorator's only job is to stamp the function
with ``__causeway_method__`` so discovery can find it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
Handler = Callable[..., Any]


def _mark(method: HttpMethod) -> Callable[[Handler], Handler]:
    def decorator(handler: Handler) -> Handler:
        existing = getattr(handler, "__causeway_method__", None)
        if existing is not None and existing != method:
            msg = (
                f"handler {handler.__name__!r} is decorated with both "
                f"@{existing.lower()} and @{method.lower()}; pick one"
            )
            raise TypeError(msg)
        handler.__causeway_method__ = method  # type: ignore[attr-defined]
        return handler

    return decorator


get = _mark("GET")
post = _mark("POST")
put = _mark("PUT")
patch = _mark("PATCH")
delete = _mark("DELETE")


def method_of(obj: Any) -> HttpMethod | None:
    """Return the HTTP method a handler is decorated with, or ``None``."""
    return getattr(obj, "__causeway_method__", None)
