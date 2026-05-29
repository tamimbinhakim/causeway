from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any

from causeway._loader import import_path
from causeway._loader import reset_module_cache as _reset_module_cache
from causeway._methods import HttpMethod, method_of
from causeway._paths import route_key_for, scope_groups_for, url_for
from causeway.middleware import Middleware, is_guard
from causeway.scope import is_dependency

if TYPE_CHECKING:
    from causeway._runtime import App

Handler = Callable[..., Any]
Provider = Callable[..., Any]


@dataclass(slots=True)
class _ScopeFrame:
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
    route_key: str
    handler: Handler
    middleware: list[Any]
    providers: dict[str, Provider]
    source: Path
    scopes: tuple[str, ...] = ()
    refreshes: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()
    idempotency: dict[str, Any] | None = None


@dataclass(slots=True)
class Discovered:
    routes: list[DiscoveredRoute] = field(default_factory=list)
    startup_hooks: list[Callable[[], Awaitable[None]]] = field(default_factory=list)
    shutdown_hooks: list[Callable[[], Awaitable[None]]] = field(default_factory=list)


def discover(routes_root: str | Path) -> Discovered:
    root = Path(routes_root)
    if not root.is_dir():
        msg = f"routes root not found: {root}"
        raise FileNotFoundError(msg)

    result = Discovered()
    _walk(root, root, _ScopeFrame(), result)
    _check_method_conflicts(result.routes)
    result.routes.sort(key=lambda r: _specificity_key(r.path))
    result.shutdown_hooks.reverse()
    for r in result.routes:
        r.handler = _bind_providers(r.handler, r.providers)
        r.handler = _compose_guards(r.handler, r.middleware)
    return result


def _specificity_key(path: str) -> tuple[tuple[int, str], ...]:
    segs: list[tuple[int, str]] = []
    for seg in path.strip("/").split("/"):
        if seg.startswith("{") and seg.endswith("}"):
            segs.append((1, seg[1:-1]))
        else:
            segs.append((0, seg))
    return tuple(segs)


def register(app: App, found: Discovered) -> None:
    for r in found.routes:
        _attach_route_metadata(r)
        decorator = _decorator_for(app, r.method)
        decorator(r.path)(r.handler)


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
        for obj in (getattr(mod, name) for name in dir(mod)):
            provided = getattr(obj, "__causeway_provide__", None)
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
    scopes = scope_groups_for(rel)
    mod = _import_path(file)
    for name in dir(mod):
        obj = getattr(mod, name)
        method = method_of(obj)
        if method is None:
            continue
        per_handler = list(getattr(obj, "__causeway_use__", ()))
        middleware = [*scope.middleware, *per_handler]
        contract = getattr(obj, "__causeway_contract__", {}) or {}
        out.routes.append(
            DiscoveredRoute(
                method=method,
                path=url,
                route_key=route_key_for(method, rel),
                handler=obj,
                middleware=middleware,
                providers=dict(scope.providers),
                source=file,
                scopes=scopes,
                refreshes=tuple(contract.get("refreshes") or ()),
                requires=_collect_requires(middleware),
                idempotency=_collect_idempotency(middleware, method),
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
    return import_path(file, label_prefix="_causeway_routes")


def reset_module_cache() -> None:
    _reset_module_cache()


def _decorator_for(app: App, method: HttpMethod) -> Callable[[str], Callable[[Handler], Handler]]:
    return getattr(app, method.lower())  # type: ignore[no-any-return]


def _attach_route_metadata(route: DiscoveredRoute) -> None:
    handler = route.handler
    handler.__causeway_route_source__ = str(route.source)  # type: ignore[attr-defined]
    handler.__causeway_route_key__ = route.route_key  # type: ignore[attr-defined]
    handler.__causeway_route_scopes__ = route.scopes  # type: ignore[attr-defined]
    handler.__causeway_route_refreshes__ = route.refreshes  # type: ignore[attr-defined]
    handler.__causeway_route_requires__ = route.requires  # type: ignore[attr-defined]
    handler.__causeway_route_idempotency__ = route.idempotency  # type: ignore[attr-defined]
    handler.__causeway_route_middleware__ = tuple(_middleware_label(m) for m in route.middleware)  # type: ignore[attr-defined]
    handler.__causeway_route_providers__ = tuple(route.providers)  # type: ignore[attr-defined]


def _middleware_label(item: Any) -> str:
    cls = item if isinstance(item, type) else type(item)
    if is_guard(item):
        return f"{getattr(item, '__module__', '?')}.{getattr(item, '__qualname__', getattr(item, '__name__', '?'))}"
    return f"{getattr(cls, '__module__', '?')}.{getattr(cls, '__qualname__', getattr(cls, '__name__', '?'))}"


def _collect_requires(middleware: list[Any]) -> tuple[str, ...]:
    out: list[str] = []
    for item in middleware:
        requires = getattr(item, "__causeway_requires__", ())
        if isinstance(requires, str):
            out.append(requires)
        else:
            out.extend(str(value) for value in requires)
    return tuple(dict.fromkeys(out))


def _collect_idempotency(middleware: list[Any], method: HttpMethod) -> dict[str, Any] | None:
    for item in middleware:
        meta = getattr(item, "__causeway_idempotency__", None)
        if not isinstance(meta, dict):
            continue
        methods = tuple(str(m).upper() for m in meta.get("methods", ()))
        if methods and method.upper() not in methods:
            continue
        return dict(meta)
    return None


def _bind_providers(handler: Handler, providers: dict[str, Provider]) -> Handler:
    import inspect as _inspect
    import typing as _typing

    from causeway._runtime import Depends

    def _key(fn: Callable[..., Any]) -> tuple[str, str] | None:
        code = getattr(fn, "__code__", None)
        if code is None:
            return None
        return (code.co_filename, getattr(code, "co_qualname", code.co_name))

    provider_keys: dict[tuple[str, str], Callable[..., Any]] = {}
    for provider in providers.values():
        key = _key(provider)
        if key is not None:
            provider_keys[key] = provider

    try:
        sig = _inspect.signature(handler, eval_str=True)
    except (TypeError, ValueError, NameError):
        try:
            sig = _inspect.signature(handler)
        except (TypeError, ValueError):
            return handler

    rewritten = False
    kept_params: list[_inspect.Parameter] = []
    bound_params: list[_inspect.Parameter] = []
    for param in sig.parameters.values():
        annotation = param.annotation
        if annotation is _inspect.Parameter.empty:
            kept_params.append(param)
            continue
        if _typing.get_origin(annotation) is not _typing.Annotated:
            kept_params.append(param)
            continue
        base, *extras = _typing.get_args(annotation)
        new_extras: list[Any] = []
        bound: Callable[..., Any] | None = None
        for extra in extras:
            if bound is None and callable(extra):
                key = _key(extra)
                if key is not None and key in provider_keys:
                    bound = provider_keys[key]
                    continue
                if is_dependency(extra):
                    bound = extra
                    continue
            new_extras.append(extra)
        if bound is None:
            kept_params.append(param)
            continue
        rewritten_annotation = base if not new_extras else _typing.Annotated[base, *new_extras]
        bound_params.append(
            param.replace(
                annotation=rewritten_annotation,
                default=Depends(bound),
                kind=_inspect.Parameter.KEYWORD_ONLY,
            ),
        )
        rewritten = True

    if not rewritten:
        return handler

    insert_at = len(kept_params)
    for index, kept_param in enumerate(kept_params):
        if kept_param.kind is _inspect.Parameter.VAR_KEYWORD:
            insert_at = index
            break
    merged = [*kept_params[:insert_at], *bound_params, *kept_params[insert_at:]]
    handler.__signature__ = sig.replace(parameters=merged)  # type: ignore[attr-defined]
    return handler


def _compose_guards(handler: Handler, middleware: list[Any]) -> Handler:
    guards = [m for m in middleware if is_guard(m)]
    mws = [m for m in middleware if not is_guard(m) and isinstance(m, Middleware)]

    if not guards and not mws:
        return handler

    if not guards:
        handler.__causeway_class_middleware__ = mws  # type: ignore[attr-defined]
        return handler

    async def with_guards(*args: Any, **kwargs: Any) -> Any:
        req = _find_request(args, kwargs)
        for g in guards:
            await g(req)
        return await handler(*args, **kwargs)

    import inspect as _inspect

    with_guards.__signature__ = _inspect.signature(handler)  # type: ignore[attr-defined]
    with_guards.__wrapped__ = handler  # type: ignore[attr-defined]
    with_guards.__annotations__ = dict(getattr(handler, "__annotations__", {}))
    handler_globals = getattr(handler, "__globals__", None)
    if handler_globals is not None:
        with_guards.__globals__.update(handler_globals)
        with_guards.__causeway_localns__ = dict(handler_globals)  # type: ignore[attr-defined]
    if mws:
        with_guards.__causeway_class_middleware__ = mws  # type: ignore[attr-defined]
    return with_guards


def _find_request(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
    for v in (*args, *kwargs.values()):
        if hasattr(v, "headers") and hasattr(v, "url"):
            return v
        request = getattr(v, "request", None)
        if request is not None and hasattr(request, "headers"):
            return request

    from causeway._runtime.context import current_context_var

    try:
        return current_context_var.get().request
    except LookupError as exc:
        msg = "guard ran outside an active request — no Request available"
        raise RuntimeError(msg) from exc


__all__ = ["Discovered", "DiscoveredRoute", "discover", "register"]
