"""Causeway-owned development server with smart route hot swapping."""

from __future__ import annotations

import ast
import asyncio
import contextlib
import importlib
import sys
import time
from collections.abc import Awaitable, Callable
from collections.abc import Sequence as SequenceABC
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import uvicorn
from rich.console import Console
from watchfiles import awatch

from causeway.routing import discover, reset_module_cache

Scope = dict[str, Any]
Message = dict[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class RouteInfo:
    method: str
    path: str
    source: str

    @property
    def key(self) -> tuple[str, str]:
        return (self.method, self.path)


@dataclass(slots=True)
class Snapshot:
    app: Any
    routes: list[RouteInfo] = field(default_factory=list)

    @property
    def route_count(self) -> int:
        return len(self.routes)


@dataclass(frozen=True, slots=True)
class ChangeDecision:
    reload: bool = True
    reason: str | None = None

    @classmethod
    def restart_required(cls, reason: str) -> ChangeDecision:
        return cls(reload=False, reason=reason)


class HotSwapApp:
    def __init__(self, snapshot: Snapshot, reporter: Reporter) -> None:
        self._snapshot = snapshot
        self._lifespan_app = snapshot.app
        self._generation = 1
        self._reporter = reporter

    @property
    def snapshot(self) -> Snapshot:
        return self._snapshot

    def swap(self, snapshot: Snapshot) -> int:
        self._generation += 1
        self._snapshot = snapshot
        return self._generation

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self._lifespan_app(scope, receive, send)
            return

        snapshot = self._snapshot
        started = time.perf_counter()
        status_code: int | None = None

        async def send_with_status(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                raw_status = message.get("status")
                if isinstance(raw_status, int):
                    status_code = raw_status
            await send(message)

        await snapshot.app(scope, receive, send_with_status)
        if scope["type"] == "http":
            self._reporter.access(scope, status_code, (time.perf_counter() - started) * 1000)


class Reporter:
    def __init__(
        self, *, host: str, port: int, module: str, console: Console | None = None
    ) -> None:
        self.host = host
        self.port = port
        self.module = module
        self.console = console or Console()

    def banner(self, snapshot: Snapshot, routes_root: Path) -> None:
        self.console.print("[bold]Causeway dev[/bold]\n")
        self.console.print(f"  server     http://{self.host}:{self.port}")
        self.console.print(f"  app        {self.module}")
        self.console.print(f"  routes     {routes_root}  {snapshot.route_count} routes")
        self.console.print("  reload     smart hot-swap\n")

    def changed(self, paths: SequenceABC[Path]) -> None:
        stamp = _stamp()
        if len(paths) == 1:
            self.console.print(f"[dim]{stamp}[/dim] changed   {_display(paths[0])}")
            return
        self.console.print(f"[dim]{stamp}[/dim] changed   {len(paths)} files")
        for path in paths:
            self.console.print(f"  {_display(path)}")

    def restart_required(self, paths: SequenceABC[Path], reason: str) -> None:
        self.console.print(f"[dim]{_stamp()}[/dim] [yellow]restart required[/yellow]")
        for path in paths:
            self.console.print(f"  {_display(path)}")
        self.console.print(f"reason: {reason}")

    def reload_ok(
        self, *, generation: int, old: Snapshot, new: Snapshot, elapsed_ms: float
    ) -> None:
        self.console.print(
            f"[dim]{_stamp()}[/dim] [green]reload ok[/green] "
            f"{elapsed_ms:.0f}ms  generation={generation}  routes={new.route_count}",
        )
        self._route_diff(old.routes, new.routes)

    def reload_failed(self, exc: BaseException) -> None:
        from causeway._traceback import format_exception

        self.console.print(f"[dim]{_stamp()}[/dim] [red]reload failed[/red] - serving previous app")
        self.console.print(format_exception(exc))

    def access(self, scope: Scope, status_code: int | None, elapsed_ms: float) -> None:
        method = str(scope.get("method", "?"))
        path = str(scope.get("path", "?"))
        status = status_code if status_code is not None else "-"
        color = "green" if isinstance(status, int) and status < 400 else "red"
        self.console.print(
            f"[dim]{_stamp()}[/dim] {method:<6} {path:<32} [{color}]{status}[/{color}] "
            f"{elapsed_ms:.0f}ms",
        )

    def _route_diff(self, old: list[RouteInfo], new: list[RouteInfo]) -> None:
        old_by_key = {route.key: route for route in old}
        new_by_key = {route.key: route for route in new}
        for key in sorted(new_by_key.keys() - old_by_key.keys()):
            route = new_by_key[key]
            self.console.print(f"  + {route.method:<6} {route.path:<32} {route.source}")
        for key in sorted(new_by_key.keys() & old_by_key.keys()):
            route = new_by_key[key]
            if route.source != old_by_key[key].source:
                self.console.print(f"  ~ {route.method:<6} {route.path:<32} {route.source}")
        for key in sorted(old_by_key.keys() - new_by_key.keys()):
            route = old_by_key[key]
            self.console.print(f"  - {route.method:<6} {route.path:<32} {route.source}")


class CausewayDevServer:
    def __init__(
        self,
        *,
        module: str,
        host: str,
        port: int,
        project: Path,
        routes_root: Path,
    ) -> None:
        self.module = module
        self.host = host
        self.port = port
        self.project = project
        self.routes_root = routes_root
        self.reporter = Reporter(host=host, port=port, module=module)

    async def run(self) -> None:
        snapshot = self._build(())
        app = HotSwapApp(snapshot, self.reporter)
        self.reporter.banner(snapshot, self.routes_root)

        config = uvicorn.Config(app, host=self.host, port=self.port, reload=False, access_log=False)
        server = uvicorn.Server(config)
        watch_task = asyncio.create_task(self._watch_loop(app))
        try:
            await server.serve()
        finally:
            watch_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await watch_task

    async def _watch_loop(self, app: HotSwapApp) -> None:
        async for changes in awatch(
            self.project,
            recursive=True,
            watch_filter=_py_only,
            debounce=100,
        ):
            paths = sorted({Path(path).resolve() for _, path in changes})
            if not paths:
                continue
            self.reporter.changed(paths)
            decision = classify_changes(paths, routes_root=self.routes_root)
            if not decision.reload:
                self.reporter.restart_required(paths, decision.reason or "unsafe change")
                continue

            old = app.snapshot
            started = time.perf_counter()
            try:
                new = self._build(paths)
            except Exception as exc:
                self.reporter.reload_failed(exc)
                continue
            generation = app.swap(new)
            self.reporter.reload_ok(
                generation=generation,
                old=old,
                new=new,
                elapsed_ms=(time.perf_counter() - started) * 1000,
            )

    def _build(self, changed: SequenceABC[Path]) -> Snapshot:
        if changed:
            reset_module_cache()
            _evict_module_target(self.module)
        app = _load_asgi(self.module)
        return Snapshot(app=app, routes=_route_infos(self.routes_root))


def classify_changes(paths: SequenceABC[Path], *, routes_root: Path) -> ChangeDecision:
    routes_root = routes_root.resolve()
    for path in paths:
        try:
            path.resolve().relative_to(routes_root)
        except ValueError:
            return ChangeDecision.restart_required(
                "non-route Python module changed; restart to refresh lifecycle/global state",
            )
        if path.name == "_scope.py" and _scope_declares_lifecycle(path):
            return ChangeDecision.restart_required(
                "_scope.py startup/shutdown changed; restart to run lifecycle hooks",
            )
    return ChangeDecision()


def run_causeway_dev(
    *,
    module: str,
    host: str,
    port: int,
    project: Path,
    routes_root: Path,
) -> None:
    server = CausewayDevServer(
        module=module,
        host=host,
        port=port,
        project=project,
        routes_root=routes_root,
    )
    asyncio.run(server.run())


def _load_asgi(target: str) -> Any:
    module_name, _, attr = target.partition(":")
    if not module_name or not attr:
        msg = "Target must be 'module:attr', e.g. 'app.app:app'."
        raise ValueError(msg)
    importlib.invalidate_caches()
    mod = importlib.import_module(module_name)
    return getattr(mod, attr)


def _route_infos(routes_root: Path) -> list[RouteInfo]:
    try:
        found = discover(routes_root)
    except FileNotFoundError:
        return []
    return [
        RouteInfo(method=route.method, path=route.path, source=_display(route.source))
        for route in found.routes
    ]


def _evict_module_target(target: str) -> None:
    module_name = target.partition(":")[0]
    if module_name:
        sys.modules.pop(module_name, None)
    importlib.invalidate_caches()


def _scope_declares_lifecycle(path: Path) -> bool:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return False
    return any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in {"startup", "shutdown"}
        for node in tree.body
    )


def _display(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def _stamp() -> str:
    return time.strftime("%H:%M:%S")


def _py_only(_change: object, path: str) -> bool:
    return path.endswith(".py")


__all__ = [
    "CausewayDevServer",
    "ChangeDecision",
    "HotSwapApp",
    "Reporter",
    "RouteInfo",
    "Snapshot",
    "classify_changes",
    "run_causeway_dev",
]
