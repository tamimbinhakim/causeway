"""File-based router.

Walks the routes tree, translates filenames into URL patterns, collects
``_middleware.py`` and ``_scope.py`` declarations per subtree, and registers
handlers onto a ``dyadpy.App``.

:func:`discover` is pure — it returns a :class:`Discovered` snapshot suitable
for ``quay diff`` and unit tests. :func:`register` is the only function that
mutates the App.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any

from quay._methods import HttpMethod, method_of
from quay._paths import url_for
from quay.middleware import Middleware, is_guard

if TYPE_CHECKING:
    from dyadpy.app import App

Handler = Callable[..., Any]
Provider = Callable[..., Any]


@dataclass(slots=True)
class _ScopeFrame:
    """Per-directory accumulator while walking the tree."""

    providers: dict[str, Provider] = field(default_factory=dict)
    middleware: list[Any] = field(default_factory=list)
    startup: Callable[[], Awaitable[None]] | None = None
    shutdown: Callable[[], Awaitable[None]] | None = None

    def merged_with(self, child: _ScopeFrame) -> _ScopeFrame:
        return _ScopeFrame(
            providers={**self.providers, **child.providers},
            middleware=[*self.middleware, *child.middleware],
            startup=child.startup or self.startup,
            shutdown=child.shutdown or self.shutdown,
        )


@dataclass(slots=True)
class DiscoveredRoute:
    method: HttpMethod
    path: str
    handler: Handler
    middleware: list[Any]
    providers: dict[str, Provider]
    source: Path


@dataclass(slots=True)
class Discovered:
    routes: list[DiscoveredRoute] = field(default_factory=list)
    startup_hooks: list[Callable[[], Awaitable[None]]] = field(default_factory=list)
    shutdown_hooks: list[Callable[[], Awaitable[None]]] = field(default_factory=list)


def discover(routes_root: str | Path) -> Discovered:
    """Walk ``routes_root`` and return everything found.

    Pure: no global state mutated, no dyadpy App touched. The output is
    trivial to snapshot for ``quay diff`` and to unit-test directly.
    """
    root = Path(routes_root)
    if not root.is_dir():
        msg = f"routes root not found: {root}"
        raise FileNotFoundError(msg)

    result = Discovered()
    _walk(root, root, _ScopeFrame(), result)
    _check_method_conflicts(result.routes)
    # Outer-most subtree shuts down last.
    result.shutdown_hooks.reverse()
    for r in result.routes:
        r.handler = _compose_guards(r.handler, r.middleware)
    return result


def register(app: App, found: Discovered) -> None:
    """Wire the discovered routes onto a ``dyadpy.App``."""
    for r in found.routes:
        decorator = _decorator_for(app, r.method)
        decorator(r.path)(r.handler)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _walk(routes_root: Path, cur: Path, inherited: _ScopeFrame, out: Discovered) -> None:
    frame = _load_scope_frame(cur)
    merged = inherited.merged_with(frame)

    if frame.startup is not None:
        out.startup_hooks.append(frame.startup)
    if frame.shutdown is not None:
        out.shutdown_hooks.append(frame.shutdown)

    for entry in sorted(cur.iterdir(), key=lambda p: p.name):
        if entry.name.startswith("."):
            continue
        if entry.is_dir():
            if entry.name.startswith("_"):
                continue
            _walk(routes_root, entry, merged, out)
            continue
        if entry.suffix != ".py" or entry.name.startswith("_"):
            continue
        _load_route_file(routes_root, entry, merged, out)


def _load_scope_frame(directory: Path) -> _ScopeFrame:
    frame = _ScopeFrame()
    middleware_file = directory / "_middleware.py"
    scope_file = directory / "_scope.py"

    if middleware_file.is_file():
        mod = _import_path(middleware_file)
        items: Iterable[Any] = getattr(mod, "middleware", ()) or ()
        items = list(items)
        for item in items:
            if not (is_guard(item) or isinstance(item, Middleware)):
                msg = (
                    f"{middleware_file}: every entry in `middleware = [...]` must be a "
                    "Middleware instance or a @guard-decorated function"
                )
                raise TypeError(msg)
        frame.middleware = items

    if scope_file.is_file():
        mod = _import_path(scope_file)
        for name in dir(mod):
            obj = getattr(mod, name)
            provided = getattr(obj, "__quay_provide__", None)
            if provided is None:
                continue
            if provided in frame.providers:
                msg = (
                    f"{scope_file}: two providers registered under name "
                    f"{provided!r}; names must be unique within a scope file"
                )
                raise TypeError(msg)
            frame.providers[provided] = obj
        frame.startup = getattr(mod, "startup", None)
        frame.shutdown = getattr(mod, "shutdown", None)

    return frame


def _load_route_file(
    routes_root: Path,
    file: Path,
    scope: _ScopeFrame,
    out: Discovered,
) -> None:
    rel = PurePosixPath(file.relative_to(routes_root).as_posix())
    url = url_for(rel)
    mod = _import_path(file)
    for name in dir(mod):
        obj = getattr(mod, name)
        method = method_of(obj)
        if method is None:
            continue
        out.routes.append(
            DiscoveredRoute(
                method=method,
                path=url,
                handler=obj,
                middleware=list(scope.middleware),
                providers=dict(scope.providers),
                source=file,
            ),
        )


def _check_method_conflicts(routes: list[DiscoveredRoute]) -> None:
    seen: dict[tuple[HttpMethod, str], Path] = {}
    for r in routes:
        key = (r.method, r.path)
        prev = seen.get(key)
        if prev is not None and prev != r.source:
            msg = f"two handlers registered for {r.method} {r.path}: {prev} and {r.source}"
            raise TypeError(msg)
        seen[key] = r.source


def _import_path(file: Path) -> Any:
    """Load a Python file by path. Brackets in the filename are fine here —
    ``spec_from_file_location`` doesn't care, and the module name we hand it
    is purely a label that never participates in Python's import system.
    """
    label = file.with_suffix("").as_posix().replace("/", ".").replace("[", "_").replace("]", "_")
    module_name = f"_quay_routes_{label}"
    spec = importlib.util.spec_from_file_location(module_name, file)
    if spec is None or spec.loader is None:
        msg = f"could not build import spec for {file}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _decorator_for(app: App, method: HttpMethod) -> Callable[[str], Callable[[Handler], Handler]]:
    return getattr(app, method.lower())  # type: ignore[no-any-return]


def _compose_guards(handler: Handler, middleware: list[Any]) -> Handler:
    """Wrap ``handler`` so any ``@guard`` items run before the body.

    Class-based ``Middleware`` instances ride on the wrapped function as
    ``__quay_class_middleware__`` for the ASGI layer to pick up.
    """
    guards = [m for m in middleware if is_guard(m)]
    mws = [m for m in middleware if isinstance(m, Middleware)]

    if not guards and not mws:
        return handler

    if not guards:
        handler.__quay_class_middleware__ = mws  # type: ignore[attr-defined]
        return handler

    async def with_guards(*args: Any, **kwargs: Any) -> Any:
        req = _find_request(args, kwargs)
        for g in guards:
            await g(req)
        return await handler(*args, **kwargs)

    # Preserve dyadpy's view of the signature and the handler's annotation
    # namespace — without this, string forward-refs (``Any``, user Structs)
    # fail to resolve when dyadpy inspects the wrapper.
    import inspect as _inspect

    with_guards.__signature__ = _inspect.signature(handler)  # type: ignore[attr-defined]
    with_guards.__wrapped__ = handler  # type: ignore[attr-defined]
    with_guards.__annotations__ = dict(getattr(handler, "__annotations__", {}))
    handler_globals = getattr(handler, "__globals__", None)
    if handler_globals is not None:
        with_guards.__globals__.update(handler_globals)  # type: ignore[attr-defined]
        with_guards.__dyadpy_localns__ = dict(handler_globals)  # type: ignore[attr-defined]
    if mws:
        with_guards.__quay_class_middleware__ = mws  # type: ignore[attr-defined]
    return with_guards


def _find_request(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
    """Locate the Starlette Request in a handler's arguments.

    Falls back to dyadpy's per-request contextvar when the handler doesn't
    take the Request directly.
    """
    for v in (*args, *kwargs.values()):
        if hasattr(v, "headers") and hasattr(v, "url"):
            return v
        request = getattr(v, "request", None)
        if request is not None and hasattr(request, "headers"):
            return request

    from dyadpy.context import current_context_var

    try:
        return current_context_var.get().request
    except LookupError as exc:
        msg = "guard ran outside an active dyadpy request — no Request available"
        raise RuntimeError(msg) from exc


__all__ = ["Discovered", "DiscoveredRoute", "discover", "register"]
