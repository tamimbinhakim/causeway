"""Application factory.

Two entry points: :func:`create_app` (dynamic, walks the routes tree at
import time) and :func:`create_app_frozen` (AOT, takes a pre-built
:class:`Discovered`). They share assembly via :func:`_assemble`; the
binary build path goes through the frozen variant.
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from dyadpy import App
from starlette.applications import Starlette
from starlette.middleware import Middleware as StarletteMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Mount

from causeway.diagnostics import attach as attach_diagnostics
from causeway.errors import error_renderer
from causeway.health import attach as attach_health
from causeway.middleware import Middleware as CausewayMiddleware
from causeway.observability import RequestIdMiddleware
from causeway.routing import Discovered, discover, register


def create_app(
    routes_root: str | Path = "app/routes",
    *,
    settings: Any = None,
    diagnostics: bool = True,
    request_id: bool = True,
    error_renderer_: bool = True,
) -> Any:
    """Build a runnable ASGI app from a routes directory.

    Composition (outermost → innermost):
    request-id → class middleware collected across scopes → dyadpy.App.
    Errors raised from inside any handler land in the problem+json renderer.
    Health endpoints (``/healthz``, ``/readyz``) attach unconditionally; the
    diagnostics endpoint (``/__causeway``) is opt-out via ``diagnostics=False``.
    """
    found = discover(routes_root)
    return _assemble(
        found,
        settings=settings,
        diagnostics=diagnostics,
        request_id=request_id,
        error_renderer_=error_renderer_,
    )


def create_app_frozen(
    found: Discovered,
    *,
    settings: Any = None,
    diagnostics: bool = False,
    request_id: bool = True,
    error_renderer_: bool = True,
) -> Any:
    """Build a runnable ASGI app from a :class:`Discovered` produced at build time.

    The dev surface (``/__causeway``) is always stripped in binary mode
    regardless of the caller's preference.
    """
    if _build_mode_is_binary() and diagnostics:
        diagnostics = False
    return _assemble(
        found,
        settings=settings,
        diagnostics=diagnostics,
        request_id=request_id,
        error_renderer_=error_renderer_,
    )


def _assemble(
    found: Discovered,
    *,
    settings: Any,
    diagnostics: bool,
    request_id: bool,
    error_renderer_: bool,
) -> Any:
    inner = App()
    register(inner, found)
    attach_health(inner)
    if diagnostics:
        attach_diagnostics(inner, settings=settings)

    middleware: list[StarletteMiddleware] = []
    if request_id:
        middleware.append(StarletteMiddleware(RequestIdMiddleware))
    for instance in _collect_class_middleware(found):
        middleware.append(StarletteMiddleware(BaseHTTPMiddleware, dispatch=instance))

    exception_handlers: dict[Any, Any] = {}
    if error_renderer_:
        exception_handlers[Exception] = error_renderer

    @contextlib.asynccontextmanager
    async def lifespan(_: Any) -> AsyncIterator[None]:
        for hook in found.startup_hooks:
            await hook()
        try:
            yield
        finally:
            for hook in found.shutdown_hooks:
                await hook()

    return Starlette(
        routes=[Mount("/", app=inner)],
        middleware=middleware,
        exception_handlers=exception_handlers,
        lifespan=lifespan,
    )


def _build_mode_is_binary() -> bool:
    return os.environ.get("CAUSEWAY_BUILD_MODE") == "binary"


def _collect_class_middleware(found: Any) -> list[CausewayMiddleware]:
    """Pull every class-based ``Middleware`` instance off the discovered routes.

    Guards live inline on the handler; class middleware wraps the whole ASGI
    chain. We deduplicate by identity so the same instance attached to
    multiple subtrees only wraps the app once.
    """
    seen: dict[int, CausewayMiddleware] = {}
    for route in found.routes:
        recorded = getattr(route.handler, "__causeway_class_middleware__", None)
        if not recorded:
            continue
        for mw in recorded:
            seen.setdefault(id(mw), mw)
    return list(seen.values())


__all__ = ["create_app", "create_app_frozen"]
