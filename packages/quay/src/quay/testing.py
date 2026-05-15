"""Testing kit.

:class:`TestApp` is the public surface — every other helper is built on top.
A test mounts the app, exercises it with httpx, and asserts on responses.
DI overrides go through the same scope machinery as production code, so
there is no separate "test injection" concept to learn.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
from dyadpy import App

from quay.health import attach as attach_health
from quay.routing import discover, register


class TestApp:
    """Wraps a Quay app for in-process testing.

    Build one of these per test (or per fixture). The class exposes ``.get``
    / ``.post`` / ``.put`` / ``.patch`` / ``.delete`` that proxy to an
    ``httpx.AsyncClient`` over an ``ASGITransport`` — no network, no
    uvicorn, just direct ASGI dispatch.
    """

    # pytest's auto-discovery treats classes prefixed with "Test" as test
    # classes. Disable that so our public class doesn't trip the collector.
    __test__ = False

    def __init__(self, app: App) -> None:
        self._app = app
        self._overrides: dict[Callable[..., Any], Callable[..., Any]] = {}

    @classmethod
    def from_routes(cls, routes_root: str | Path) -> TestApp:
        """Discover ``routes_root`` and wire a fresh App. Health endpoints attach."""
        app = App()
        register(app, discover(routes_root))
        attach_health(app)
        return cls(app)

    @classmethod
    def wrap(cls, app: App) -> TestApp:
        """Wrap an existing ``dyadpy.App`` — useful for app-factory patterns."""
        return cls(app)

    @asynccontextmanager
    async def override(
        self,
        provider: Callable[..., Any],
        replacement: Callable[..., Any],
    ) -> AsyncIterator[None]:
        """Swap a DI provider for the duration of a block.

        Replacements honor the same shape as the original (sync function,
        async function, sync generator, async generator). The original is
        restored on exit even if the block raises.
        """
        original_code = provider.__code__
        provider.__code__ = replacement.__code__
        try:
            yield
        finally:
            provider.__code__ = original_code

    @asynccontextmanager
    async def client(self) -> AsyncIterator[httpx.AsyncClient]:
        transport = httpx.ASGITransport(app=self._app)  # type: ignore[arg-type]
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    async def request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        async with self.client() as c:
            return await c.request(method, path, **kwargs)

    async def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("PUT", path, **kwargs)

    async def patch(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("PATCH", path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("DELETE", path, **kwargs)


@asynccontextmanager
async def stub(provider: Callable[..., Any], value: Any) -> AsyncIterator[None]:
    """Replace a provider with one that returns ``value``.

    Convenience wrapper around :meth:`TestApp.override` for the common case
    of "I just want this dependency to be the literal ``value``".
    """

    async def constant() -> Any:
        return value

    original_code = provider.__code__
    provider.__code__ = constant.__code__
    try:
        yield
    finally:
        provider.__code__ = original_code


from quay.tasks import tasks_eager  # noqa: E402 - module re-export

__all__ = ["TestApp", "stub", "tasks_eager"]
