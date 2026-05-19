"""``_scope.py`` semantics: scoped DI providers + optional lifespan hooks.

A ``_scope.py`` file declares request-scoped providers via ``@provide("name")``
and may export ``startup()`` / ``shutdown()`` async functions that fire when
the app starts up and shuts down. Providers compose by subtree: the inner-most
provider for a given name wins; outer providers are inherited.

For now the public surface is small on purpose. Wider features (provider
introspection, named overrides outside scope files, scope-aware caching
beyond what dyadpy already gives us) can land later without churning this.
"""

from __future__ import annotations

import inspect
import typing
from collections.abc import Callable
from typing import Any

Provider = Callable[..., Any]


def provide(name: str) -> Callable[[Provider], Provider]:
    """Mark a provider in a ``_scope.py`` file.

    The decorator stamps ``__causeway_provide__`` on the function so the file
    router can collect it. The provider itself is a plain function (sync,
    async, or generator) — Causeway hands it to ``dyadpy.Depends`` unchanged.
    """
    if not name:
        msg = "provide(name) requires a non-empty string"
        raise ValueError(msg)

    def decorator(fn: Provider) -> Provider:
        fn.__causeway_provide__ = name  # type: ignore[attr-defined]
        return fn

    return decorator


def provider_name(obj: Any) -> str | None:
    """Return the provider name a function was registered under, or ``None``."""
    return getattr(obj, "__causeway_provide__", None)


def dependency(fn: Provider) -> Any:
    """Wrap a resolver as an ``Annotated`` alias usable directly on handlers.

    The function's declared return type becomes the user-visible type; the
    function itself is bound as a request-scoped resolver. Combines the value
    and the guard check in one place:

        @dependency
        async def CurrentUser(req: Request) -> User:
            user = await load_user(req)
            if user is None:
                raise Unauthorized("sign in")
            return user

        @get
        async def show(me: CurrentUser) -> User: ...

    Unlike ``@provide``, the dependency does not need to live in a
    ``_scope.py`` file — it is bound by the callable's identity in the
    handler's ``Annotated`` extras.
    """
    sig = inspect.signature(fn)
    if sig.return_annotation is inspect.Signature.empty:
        msg = f"@dependency {fn.__name__!r} must declare a return type annotation"
        raise TypeError(msg)
    fn.__causeway_dependency__ = True  # type: ignore[attr-defined]
    return typing.Annotated[sig.return_annotation, fn]


def is_dependency(obj: Any) -> bool:
    return bool(getattr(obj, "__causeway_dependency__", False))
