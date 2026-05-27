"""TestApp + diagnostics tests."""

from __future__ import annotations

from pathlib import Path

from causeway._runtime import App
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
    app = TestApp.from_routes(routes, diagnostics=True)

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


async def test_class_middleware_fires_in_test_app(tmp_path: Path) -> None:
    """``TestApp.from_routes`` must wrap the inner App so ``Middleware``
    instances declared in ``_middleware.py`` actually run — without that
    wrap, permission guards and idempotency checks silently no-op in tests.
    """
    routes = tmp_path / "routes"
    _write(
        routes,
        "index.py",
        "from causeway import get\n@get\nasync def root() -> dict: return {'ok': True}\n",
    )
    _write(
        routes,
        "_middleware.py",
        (
            "from causeway import Middleware\n"
            "from starlette.responses import JSONResponse\n"
            "\n"
            "\n"
            "class Stamp(Middleware):\n"
            "    async def __call__(self, req, call_next):\n"
            "        resp = await call_next(req)\n"
            "        resp.headers['x-mw-fired'] = '1'\n"
            "        return resp\n"
            "\n"
            "\n"
            "middleware = [Stamp()]\n"
        ),
    )
    app = TestApp.from_routes(routes)
    resp = await app.get("/")
    assert resp.status_code == 200
    assert resp.headers.get("x-mw-fired") == "1"
