from __future__ import annotations

import inspect
import typing
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from typing import Any, ParamSpec, TypeVar, cast, overload

P = ParamSpec("P")
T = TypeVar("T")
Provider = Callable[P, T]
AnyProvider = Callable[..., Any]


def provide(name: str) -> Callable[[Provider[P, T]], Provider[P, T]]:
    if not name:
        msg = "provide(name) requires a non-empty string"
        raise ValueError(msg)

    def decorator(fn: Provider[P, T]) -> Provider[P, T]:
        fn.__causeway_provide__ = name  # type: ignore[attr-defined]
        return fn

    return decorator


def provider_name(obj: Any) -> str | None:
    return getattr(obj, "__causeway_provide__", None)


@overload
def dependency(fn: Callable[P, Awaitable[T]]) -> type[T]: ...


@overload
def dependency(fn: Callable[P, AsyncIterator[T]]) -> type[T]: ...


@overload
def dependency(fn: Callable[P, Iterator[T]]) -> type[T]: ...


@overload
def dependency(fn: Callable[P, T]) -> type[T]: ...


def dependency(fn: AnyProvider) -> Any:
    sig = inspect.signature(fn)
    if sig.return_annotation is inspect.Signature.empty:
        msg = f"@dependency {fn.__name__!r} must declare a return type annotation"
        raise TypeError(msg)
    fn.__causeway_dependency__ = True  # type: ignore[attr-defined]
    return cast(Any, typing.Annotated[sig.return_annotation, fn])


def is_dependency(obj: Any) -> bool:
    return bool(getattr(obj, "__causeway_dependency__", False))
