from __future__ import annotations

import contextlib
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import re

from starlette.applications import Starlette
from starlette.middleware import Middleware as StarletteMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Mount, compile_path

import causeway.events as _events
import causeway.plugins as _plugins
import causeway.webhooks as _webhooks  # noqa: F401 — wires fan-out into Event.emit at import
from causeway._loader import import_path
from causeway._runtime import App
from causeway._traceback import ExceptionShield
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
    inner = App(exception_handler=error_renderer if error_renderer_ else None)
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

    starlette = Starlette(
        routes=[Mount("/", app=inner)],
        middleware=middleware,
        exception_handlers=exception_handlers,
        lifespan=lifespan,
    )
    # Starlette's ServerErrorMiddleware re-raises every unhandled exception
    # after the registered handler renders the 500 response. Without this
    # shield, that re-raise reaches the ASGI server and a giant Python
    # traceback gets printed on top of our compact one.
    return ExceptionShield(starlette)


def _discover_plugins(routes_root: str | Path) -> None:
    _plugins.discover()
    app_root = Path(routes_root).parent
    plugins_file = app_root / "plugins.py"
    if plugins_file.is_file():
        import_path(plugins_file, label_prefix="_causeway_plugins")


def _discover_app_lifespan(routes_root: str | Path) -> Any:
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
    if not Path(events_root).is_dir():
        return None
    snapshot = _events.discover(
        events_root,
        listeners_root=listeners_root if Path(listeners_root).is_dir() else None,
    )
    for entry in _visible_py_tree(Path(subscribers_root)):
        import_path(entry, label_prefix="_causeway_subscribers")
    return snapshot


def _build_mode_is_binary() -> bool:
    return os.environ.get("CAUSEWAY_BUILD_MODE") == "binary"


def _collect_class_middleware(found: Any) -> list[StarletteMiddleware]:
    seen: dict[int, tuple[CausewayMiddleware, dict[str, list[re.Pattern[str]]]]] = {}
    order: list[int] = []
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
    async def dispatch(request: Any, call_next: Any) -> Any:
        regexes = by_method.get(request.method)
        if regexes is not None:
            path = request.url.path
            for regex in regexes:
                if regex.fullmatch(path) is not None:
                    return await mw(request, call_next)
        return await call_next(request)

    return dispatch


def _visible_py_tree(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    resolved = root.resolve()
    return [
        entry
        for entry in sorted(root.rglob("*.py"))
        if not any(p.startswith(("_", ".")) for p in entry.resolve().relative_to(resolved).parts)
    ]


__all__ = ["create_app", "create_app_frozen"]
