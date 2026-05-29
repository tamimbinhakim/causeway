"""Causeway App Graph.

The graph is the framework-owned, agent-readable shape of an app: public route
keys, HTTP paths, source files, scopes, contracts, middleware, providers,
events, tasks, and plugins. It is deliberately metadata-only; request execution
continues to run through the normal runtime.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

from causeway.events import Discovered as EventsDiscovered
from causeway.events import all_events
from causeway.plugins import registered
from causeway.tasks import cron_jobs, registered_tasks

if TYPE_CHECKING:
    from causeway._runtime.app import App, Route


@dataclass(slots=True)
class GraphParam:
    name: str
    alias: str
    location: str
    required: bool


@dataclass(slots=True)
class GraphRoute:
    route_key: str
    method: str
    http_path: str
    source: str | None
    scopes: tuple[str, ...] = ()
    params: tuple[GraphParam, ...] = ()
    response: str | None = None
    errors: tuple[str, ...] = ()
    streams: bool = False
    refreshes: tuple[str, ...] = ()
    middleware: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()
    idempotency: dict[str, Any] | None = None
    providers: tuple[str, ...] = ()


@dataclass(slots=True)
class GraphTask:
    name: str
    queue: str
    retries: int
    backoff: str
    cron: str | None = None


@dataclass(slots=True)
class GraphEvent:
    name: str
    class_name: str
    module: str
    webhook: bool
    listeners: int
    subscribers: int


@dataclass(slots=True)
class GraphPlugin:
    adapter: str
    module: str
    contract_version: str


@dataclass(slots=True)
class AppGraph:
    routes: list[GraphRoute] = field(default_factory=list)
    providers: list[str] = field(default_factory=list)
    plugins: list[GraphPlugin] = field(default_factory=list)
    tasks: list[GraphTask] = field(default_factory=list)
    events: list[GraphEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_graph(app: App, *, events: EventsDiscovered | None = None) -> AppGraph:
    routes = [_route_to_graph(route) for route in app.routes]
    providers = sorted({provider for route in routes for provider in route.providers})
    return AppGraph(
        routes=routes,
        providers=providers,
        plugins=_plugins(),
        tasks=_tasks(),
        events=_events(events),
    )


def graph_dict(app: App, *, events: EventsDiscovered | None = None) -> dict[str, Any]:
    return build_graph(app, events=events).to_dict()


def _route_to_graph(route: Route) -> GraphRoute:
    plan = route.plan
    if plan is None:
        from causeway._runtime.runtime import build_plan

        plan = build_plan(route.handler, route.path)
        route.plan = plan

    params = tuple(
        GraphParam(
            name=p.name,
            alias=p.alias,
            location=str(p.location),
            required=p.required,
        )
        for p in plan.params
        if p.location is not None
    )
    response = _type_name(plan.event_type if plan.streams else plan.return_annotation)
    return GraphRoute(
        route_key=route.route_key or f"{route.method} {route.path}",
        method=route.method,
        http_path=route.path,
        source=route.source,
        scopes=route.scopes,
        params=params,
        response=response,
        errors=tuple(exc.__name__ for exc in plan.raises),
        streams=plan.streams,
        refreshes=route.refreshes,
        middleware=route.middleware,
        requires=route.requires,
        idempotency=route.idempotency,
        providers=route.providers,
    )


def _type_name(value: Any) -> str | None:
    if value is None:
        return None
    name = getattr(value, "__qualname__", None)
    module = getattr(value, "__module__", None)
    if isinstance(name, str):
        return f"{module}.{name}" if module and module != "builtins" else name
    return str(value)


def _plugins() -> list[GraphPlugin]:
    return [
        GraphPlugin(
            adapter=type(adapter).__name__,
            module=type(adapter).__module__,
            contract_version=str(getattr(adapter, "contract_version", "?")),
        )
        for adapter in registered()
    ]


def _tasks() -> list[GraphTask]:
    cron_by_task = {f"{ref.module}.{ref.name}": expr for ref, expr in cron_jobs()}
    return [
        GraphTask(
            name=key,
            queue=ref.queue,
            retries=ref.retries,
            backoff=ref.backoff,
            cron=cron_by_task.get(key),
        )
        for key, ref in registered_tasks().items()
    ]


def _events(discovered: EventsDiscovered | None) -> list[GraphEvent]:
    event_map = discovered.events if discovered is not None else all_events()
    return [
        GraphEvent(
            name=name,
            class_name=cls.__qualname__,
            module=cls.__module__,
            webhook=bool(getattr(cls, "webhook", False)),
            listeners=len(getattr(cls, "_listeners", ())),
            subscribers=len(getattr(cls, "_subscribers", ())),
        )
        for name, cls in sorted(event_map.items())
    ]


__all__ = [
    "AppGraph",
    "GraphEvent",
    "GraphParam",
    "GraphPlugin",
    "GraphRoute",
    "GraphTask",
    "build_graph",
    "graph_dict",
]
