from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, ParamSpec, TypeVar

HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
P = ParamSpec("P")
R = TypeVar("R")
Handler = Callable[P, R]
AnyHandler = Callable[..., Any]


def _mark(method: HttpMethod) -> Callable[[Handler[P, R]], Handler[P, R]]:
    def decorator(handler: Handler[P, R]) -> Handler[P, R]:
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


get: Callable[[Handler[P, R]], Handler[P, R]] = _mark("GET")
post: Callable[[Handler[P, R]], Handler[P, R]] = _mark("POST")
put: Callable[[Handler[P, R]], Handler[P, R]] = _mark("PUT")
patch: Callable[[Handler[P, R]], Handler[P, R]] = _mark("PATCH")
delete: Callable[[Handler[P, R]], Handler[P, R]] = _mark("DELETE")


def method_of(obj: Any) -> HttpMethod | None:
    return getattr(obj, "__causeway_method__", None)
