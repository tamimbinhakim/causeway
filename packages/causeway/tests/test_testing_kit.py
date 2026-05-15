"""TestApp + diagnostics tests."""

from __future__ import annotations

from pathlib import Path

from dyadpy import App

from causeway.diagnostics import attach as attach_diagnostics
from causeway.diagnostics import snapshot
from causeway.testing import TestApp


def _write(root: Path, rel: str, body: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)


async def test_testapp_from_routes_serves_handler(tmp_path: Path) -> None:
    routes = tmp_path / "routes"
    _write(
        routes,
        "index.py",
        "from causeway import get\n@get\nasync def root() -> dict: return {'ok': True}\n",
    )
    app = TestApp.from_routes(routes)
    resp = await app.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


async def test_testapp_includes_health_endpoints(tmp_path: Path) -> None:
    routes = tmp_path / "routes"
    _write(routes, "index.py", "from causeway import get\n@get\nasync def r() -> dict: return {}\n")
    app = TestApp.from_routes(routes)
    resp = await app.get("/healthz")
    assert resp.status_code == 200


async def test_diagnostics_snapshot_includes_known_fields() -> None:
    data = snapshot()
    assert set(data.keys()) >= {"routes", "tasks", "cron", "plugins", "config"}


async def test_diagnostics_endpoint_returns_routes(tmp_path: Path) -> None:
    routes = tmp_path / "routes"
    _write(routes, "index.py", "from causeway import get\n@get\nasync def r() -> dict: return {}\n")
    app = TestApp.from_routes(routes)
    attach_diagnostics(app._app)

    resp = await app.get("/__causeway")
    assert resp.status_code == 200
    data = resp.json()
    paths = [r["path"] for r in data["routes"]]
    assert "/" in paths
    assert "/__causeway" in paths


def test_wrap_existing_app_passthrough() -> None:
    raw = App()
    wrapped = TestApp.wrap(raw)
    assert wrapped is not None
