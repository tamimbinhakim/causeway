"""OTel middleware test."""

# pyright: basic

from __future__ import annotations

from starlette.testclient import TestClient

from causeway._runtime import App
from causeway._runtime.otel import instrument


def test_instrument_wraps_and_passes_through() -> None:
    app = App()

    @app.get("/ok")
    async def ok() -> dict[str, bool]:
        return {"ok": True}

    wrapped = instrument(app)
    client = TestClient(wrapped)  # type: ignore[arg-type]
    r = client.get("/ok")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
