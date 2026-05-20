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
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import re

from dyadpy import App
from starlette.applications import Starlette
from starlette.middleware import Middleware as StarletteMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Mount, compile_path

import causeway.events as _events
import causeway.plugins as _plugins
import causeway.webhooks as _webhooks  # noqa: F401 — wires fan-out into Event.emit at import
from causeway._loader import import_path
from causeway.diagnostics import attach as attach_diagnostics
from causeway.errors import error_renderer
from causeway.health import attach as attach_health
from causeway.middleware import Middleware as CausewayMiddleware
from causeway.observability import RequestIdMiddleware
from causeway.routing import Discovered, discover, register


def create_app(
    routes_root: str | Path = "app/routes",
    *,
    events_root: str | Path = "app/events",
    listeners_root: str | Path = "app/listeners",
    subscribers_root: str | Path = "app/subscribers",
    settings: Any = None,
    diagnostics: bool = True,
    request_id: bool = True,
    error_renderer_: bool = True,
) -> Any:
    """Build a runnable ASGI app from a routes directory.

    Composition (outermost → innermost):
    request-id → class middleware collected across scopes → dyadpy.App.
    Class middleware is path-gated to the routes that declared it (subtree
    via ``_middleware.py`` or single-route via ``@use``); a request to a
    different route walks past the middleware untouched.
    Errors raised from inside any handler land in the problem+json renderer.
    Health endpoints (``/healthz``, ``/readyz``) attach unconditionally; the
    diagnostics endpoint (``/__causeway``) is opt-out via ``diagnostics=False``.

    File-based discovery walks three trees if they exist:

    - ``events_root`` — :class:`~causeway.events.Event` subclasses register
      themselves via ``__init_subclass__`` when imported.
    - ``listeners_root`` — every ``.py`` is imported so its
      ``@<Event>.listen`` decorators run.
    - ``subscribers_root`` — every ``.py`` is imported so
      :class:`~causeway.webhooks.Subscriber` instances register against
      their event classes' ``_subscribers`` lists.

    Missing folders are skipped silently. The class itself is the bus; no
    separate ``EventBus`` plugin is installed.
    """
    _discover_plugins(routes_root)
    found = discover(routes_root)
    events = _discover_events(events_root, listeners_root, subscribers_root)
    app_lifespan = _discover_app_lifespan(routes_root)
    return _assemble(
        found,
        events=events,
        app_lifespan=app_lifespan,
        settings=settings,
        diagnostics=diagnostics,
        request_id=request_id,
        error_renderer_=error_renderer_,
    )


def create_app_frozen(
    found: Discovered,
    *,
    events: _events.Discovered | None = None,
    settings: Any = None,
    diagnostics: bool = False,
    request_id: bool = True,
    error_renderer_: bool = True,
) -> Any:
    """Build a runnable ASGI app from a :class:`Discovered` produced at build time.

    The dev surface (``/__causeway``) is always stripped in binary mode
    regardless of the caller's preference. ``events`` is accepted for
    API compatibility with the frozen-runtime path but unused — event
    classes register themselves at import time.
    """
    if _build_mode_is_binary() and diagnostics:
        diagnostics = False
    return _assemble(
        found,
        events=events,
        app_lifespan=None,
        settings=settings,
        diagnostics=diagnostics,
        request_id=request_id,
        error_renderer_=error_renderer_,
    )


def _assemble(
    found: Discovered,
    *,
    events: _events.Discovered | None,
    app_lifespan: Any,
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
    middleware.extend(_collect_class_middleware(found))

    exception_handlers: dict[Any, Any] = {}
    if error_renderer_:
        exception_handlers[Exception] = error_renderer

    _ = events  # discovery already had its side effects; nothing to install

    @contextlib.asynccontextmanager
    async def lifespan(_: Any) -> AsyncIterator[None]:
        if app_lifespan is not None:
            startup = getattr(app_lifespan, "startup", None)
            if callable(startup):
                await startup()
        await _plugins.startup_all(settings)
        for hook in found.startup_hooks:
            await hook()
        try:
            yield
        finally:
            for hook in found.shutdown_hooks:
                await hook()
            await _plugins.shutdown_all()
            if app_lifespan is not None:
                shutdown = getattr(app_lifespan, "shutdown", None)
                if callable(shutdown):
                    await shutdown()

    return Starlette(
        routes=[Mount("/", app=inner)],
        middleware=middleware,
        exception_handlers=exception_handlers,
        lifespan=lifespan,
    )


def _discover_plugins(routes_root: str | Path) -> None:
    """Load entry-point plugins, then the app-local ``plugins.py`` if present."""
    _plugins.discover()
    app_root = Path(routes_root).parent
    plugins_file = app_root / "plugins.py"
    if plugins_file.is_file():
        import_path(plugins_file, label_prefix="_causeway_plugins")


def _discover_app_lifespan(routes_root: str | Path) -> Any:
    """Load app-level ``lifespan.py`` next to the routes tree if present."""
    app_root = Path(routes_root).parent
    lifespan_file = app_root / "lifespan.py"
    if not lifespan_file.is_file():
        return None
    return import_path(lifespan_file, label_prefix="_causeway_lifespan")


def _discover_events(
    events_root: str | Path,
    listeners_root: str | Path,
    subscribers_root: str | Path,
) -> _events.Discovered | None:
    """Walk the three discovery trees. Returns the snapshot or ``None`` if
    the events folder is absent."""
    if not Path(events_root).is_dir():
        return None
    snapshot = _events.discover(
        events_root,
        listeners_root=listeners_root if Path(listeners_root).is_dir() else None,
    )
    # Subscribers register themselves on import; no need to keep references.
    sub_root = Path(subscribers_root)
    if sub_root.is_dir():
        root = sub_root.resolve()
        for entry in sorted(sub_root.rglob("*.py")):
            rel = entry.resolve().relative_to(root)
            if any(p.startswith("_") or p.startswith(".") for p in rel.parts):
                continue
            import_path(entry, label_prefix="_causeway_subscribers")
    return snapshot


def _build_mode_is_binary() -> bool:
    return os.environ.get("CAUSEWAY_BUILD_MODE") == "binary"


def _collect_class_middleware(found: Any) -> list[StarletteMiddleware]:
    """Build path-gated Starlette middleware entries for class ``Middleware``.

    Each unique ``Middleware`` instance attaches to the ASGI chain exactly
    once, but its dispatch only fires for routes that declared it. This makes
    a ``_middleware.py`` apply only to its subtree, and ``@use(Middleware())``
    apply only to that handler — without spinning up one Starlette middleware
    per route.

    Insertion order follows first-occurrence in the discovered route list,
    which mirrors outer-scope-before-inner-scope because parent middleware
    is prepended in ``_ScopeFrame.merged_with``.
    """
    seen: dict[int, tuple[CausewayMiddleware, dict[str, list[re.Pattern[str]]]]] = {}
    order: list[int] = []
    # One regex per declared path string, reused across middleware that gate
    # on the same route — avoids redundant ``compile_path`` work at boot.
    path_cache: dict[str, re.Pattern[str]] = {}

    for route in found.routes:
        recorded = getattr(route.handler, "__causeway_class_middleware__", None)
        if not recorded:
            continue
        regex = path_cache.get(route.path)
        if regex is None:
            regex, _, _ = compile_path(route.path)
            path_cache[route.path] = regex
        method = route.method.upper()
        for mw in recorded:
            mid = id(mw)
            entry = seen.get(mid)
            if entry is None:
                entry = (mw, {})
                seen[mid] = entry
                order.append(mid)
            entry[1].setdefault(method, []).append(regex)

    entries: list[StarletteMiddleware] = []
    for mid in order:
        mw, by_method = seen[mid]
        entries.append(
            StarletteMiddleware(BaseHTTPMiddleware, dispatch=_gated_dispatch(mw, by_method)),
        )
    return entries


def _gated_dispatch(
    mw: CausewayMiddleware,
    by_method: dict[str, list[re.Pattern[str]]],
) -> Any:
    """Wrap ``mw`` so it only runs when the request matches one of its routes.

    ASGI guarantees ``request.method`` is uppercase, so the lookup is a
    plain dict hit; only paths that map to this middleware are scanned.
    """

    async def dispatch(request: Any, call_next: Any) -> Any:
        regexes = by_method.get(request.method)
        if regexes is not None:
            path = request.url.path
            # ``fullmatch`` rather than ``match``: the compiled-path regex
            # ends in ``$`` which would otherwise accept a trailing ``\n``
            # (a decoded ``%0A``) and run middleware on a path the router
            # would later reject.
            for regex in regexes:
                if regex.fullmatch(path) is not None:
                    return await mw(request, call_next)
        return await call_next(request)

    return dispatch


__all__ = ["create_app", "create_app_frozen"]
