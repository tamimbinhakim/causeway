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

from collections.abc import Callable
from typing import Any

Provider = Callable[..., Any]


def provide(name: str) -> Callable[[Provider], Provider]:
    """Mark a provider in a ``_scope.py`` file.

    The decorator stamps ``__quay_provide__`` on the function so the file
    router can collect it. The provider itself is a plain function (sync,
    async, or generator) — Quay hands it to ``dyadpy.Depends`` unchanged.
    """
    if not name:
        msg = "provide(name) requires a non-empty string"
        raise ValueError(msg)

    def decorator(fn: Provider) -> Provider:
        fn.__quay_provide__ = name  # type: ignore[attr-defined]
        return fn

    return decorator


def provider_name(obj: Any) -> str | None:
    """Return the provider name a function was registered under, or ``None``."""
    return getattr(obj, "__quay_provide__", None)
