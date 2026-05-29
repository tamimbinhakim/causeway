from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, Literal, ParamSpec, TypeVar, overload

HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
P = ParamSpec("P")
R = TypeVar("R")
Handler = Callable[P, R]
AnyHandler = Callable[..., Any]


def _normalize_refreshes(refreshes: str | Iterable[str]) -> tuple[str, ...]:
    if isinstance(refreshes, str):
        return (refreshes,)
    return tuple(str(item) for item in refreshes)


def _decorate(
    method: HttpMethod,
    handler: Handler[P, R],
    *,
    refreshes: str | Iterable[str] = (),
) -> Handler[P, R]:
    existing = getattr(handler, "__causeway_method__", None)
    if existing is not None and existing != method:
        msg = (
            f"handler {handler.__name__!r} is decorated with both "
            f"@{existing.lower()} and @{method.lower()}; pick one"
        )
        raise TypeError(msg)
    contract = dict(getattr(handler, "__causeway_contract__", {}) or {})
    contract["refreshes"] = _normalize_refreshes(refreshes)
    handler.__causeway_method__ = method  # type: ignore[attr-defined]
    handler.__causeway_contract__ = contract  # type: ignore[attr-defined]
    return handler


def _mark(
    method: HttpMethod,
    handler: Handler[P, R] | None = None,
    *,
    refreshes: str | Iterable[str] = (),
) -> Handler[P, R] | Callable[[Handler[P, R]], Handler[P, R]]:
    def decorator(fn: Handler[P, R]) -> Handler[P, R]:
        return _decorate(method, fn, refreshes=refreshes)

    if handler is None:
        return decorator
    return decorator(handler)


@overload
def get(handler: Handler[P, R], /) -> Handler[P, R]: ...


@overload
def get(*, refreshes: str | Iterable[str] = ()) -> Callable[[Handler[P, R]], Handler[P, R]]: ...


def get(
    handler: Handler[P, R] | None = None,
    *,
    refreshes: str | Iterable[str] = (),
) -> Handler[P, R] | Callable[[Handler[P, R]], Handler[P, R]]:
    return _mark("GET", handler, refreshes=refreshes)


@overload
def post(handler: Handler[P, R], /) -> Handler[P, R]: ...


@overload
def post(*, refreshes: str | Iterable[str] = ()) -> Callable[[Handler[P, R]], Handler[P, R]]: ...


def post(
    handler: Handler[P, R] | None = None,
    *,
    refreshes: str | Iterable[str] = (),
) -> Handler[P, R] | Callable[[Handler[P, R]], Handler[P, R]]:
    return _mark("POST", handler, refreshes=refreshes)


@overload
def put(handler: Handler[P, R], /) -> Handler[P, R]: ...


@overload
def put(*, refreshes: str | Iterable[str] = ()) -> Callable[[Handler[P, R]], Handler[P, R]]: ...


def put(
    handler: Handler[P, R] | None = None,
    *,
    refreshes: str | Iterable[str] = (),
) -> Handler[P, R] | Callable[[Handler[P, R]], Handler[P, R]]:
    return _mark("PUT", handler, refreshes=refreshes)


@overload
def patch(handler: Handler[P, R], /) -> Handler[P, R]: ...


@overload
def patch(*, refreshes: str | Iterable[str] = ()) -> Callable[[Handler[P, R]], Handler[P, R]]: ...


def patch(
    handler: Handler[P, R] | None = None,
    *,
    refreshes: str | Iterable[str] = (),
) -> Handler[P, R] | Callable[[Handler[P, R]], Handler[P, R]]:
    return _mark("PATCH", handler, refreshes=refreshes)


@overload
def delete(handler: Handler[P, R], /) -> Handler[P, R]: ...


@overload
def delete(*, refreshes: str | Iterable[str] = ()) -> Callable[[Handler[P, R]], Handler[P, R]]: ...


def delete(
    handler: Handler[P, R] | None = None,
    *,
    refreshes: str | Iterable[str] = (),
) -> Handler[P, R] | Callable[[Handler[P, R]], Handler[P, R]]:
    return _mark("DELETE", handler, refreshes=refreshes)


def method_of(obj: Any) -> HttpMethod | None:
    return getattr(obj, "__causeway_method__", None)
