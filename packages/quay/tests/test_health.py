"""Health endpoints + readyz aggregation."""

from __future__ import annotations

from typing import Any, ClassVar

import httpx
import pytest
from dyadpy import App

from quay.health import attach
from quay.plugins import clear, register


@pytest.fixture(autouse=True)
def _isolated_registry() -> Any:
    clear()
    yield
    clear()


async def test_healthz_always_200() -> None:
    app = App()
    attach(app)
    transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_readyz_200_when_no_plugins() -> None:
    app = App()
    attach(app)
    transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.get("/readyz")
    assert resp.status_code == 200


async def test_readyz_503_when_a_plugin_isnt_ready() -> None:
    class FailingReady:
        contract_version: ClassVar[str] = "v1.0"

        async def startup(self, settings: Any) -> None: ...

        async def shutdown(self) -> None: ...

        async def ready(self) -> bool:
            return False

    register(FailingReady())

    app = App()
    attach(app)
    transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.get("/readyz")
    assert resp.status_code == 503
    payload = resp.json()
    assert payload["status"] == "not_ready"
    assert payload["plugins"]["FailingReady"] is False


async def test_user_override_takes_precedence() -> None:
    app = App()

    @app.get("/healthz")
    async def custom() -> dict[str, str]:
        return {"status": "custom"}

    attach(app)
    transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.get("/healthz")
    assert resp.json()["status"] == "custom"
