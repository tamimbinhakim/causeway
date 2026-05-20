from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, Protocol, TypeVar, runtime_checkable

from starlette.requests import Request as Request
from starlette.responses import Response as Response

P = ParamSpec("P")
R = TypeVar("R")
CallNext = Callable[[Request], Awaitable[Response]]
GuardFn = Callable[[Request], Awaitable[None]]


@runtime_checkable
class Middleware(Protocol):
    async def __call__(self, req: Request, call_next: CallNext) -> Response: ...


def guard(fn: GuardFn) -> GuardFn:
    fn.__causeway_guard__ = True  # type: ignore[attr-defined]
    return fn


def is_guard(obj: Any) -> bool:
    return bool(getattr(obj, "__causeway_guard__", False))


MiddlewareItem = GuardFn | Middleware


def use(*items: MiddlewareItem) -> Callable[[Callable[P, R]], Callable[P, R]]:
    for item in items:
        if not (is_guard(item) or isinstance(item, Middleware)):
            msg = (
                "@use(...) entries must be a Middleware instance or a "
                f"@guard-decorated function, got {item!r}"
            )
            raise TypeError(msg)

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        existing = getattr(fn, "__causeway_use__", ())
        fn.__causeway_use__ = (*items, *existing)  # type: ignore[attr-defined]
        return fn

    return decorator


from causeway.middleware.idempotency import IdempotencyMiddleware  # noqa: E402

__all__ = [
    "CallNext",
    "GuardFn",
    "IdempotencyMiddleware",
    "Middleware",
    "MiddlewareItem",
    "Request",
    "Response",
    "guard",
    "is_guard",
    "use",
]
