"""Discovery tests: file walking, scope composition, method-conflict detection."""

from __future__ import annotations

from pathlib import Path

import pytest

import causeway
from causeway.routing import discover


def _write(root: Path, rel: str, body: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)
    return p


def test_discovers_basic_routes(tmp_path: Path) -> None:
    routes = tmp_path / "routes"
    _write(
        routes, "index.py", "from causeway import get\n@get\nasync def root() -> dict: return {}\n"
    )
    _write(
        routes, "health.py", "from causeway import get\n@get\nasync def show() -> dict: return {}\n"
    )
    _write(
        routes,
        "users/[id].py",
        "from causeway import get, patch\n"
        "@get\nasync def show(id: str) -> dict: return {'id': id}\n"
        "@patch\nasync def update(id: str) -> dict: return {'id': id}\n",
    )

    found = discover(routes)
    paths = sorted({(r.method, r.path) for r in found.routes})
    assert paths == [
        ("GET", "/"),
        ("GET", "/health"),
        ("GET", "/users/{id}"),
        ("PATCH", "/users/{id}"),
    ]


def test_strips_route_groups(tmp_path: Path) -> None:
    routes = tmp_path / "routes"
    _write(
        routes,
        "(admin)/stats.py",
        "from causeway import get\n@get\nasync def s() -> dict: return {}\n",
    )
    found = discover(routes)
    assert [(r.method, r.path) for r in found.routes] == [("GET", "/stats")]


def test_private_files_skipped(tmp_path: Path) -> None:
    routes = tmp_path / "routes"
    _write(routes, "index.py", "from causeway import get\n@get\nasync def r() -> dict: return {}\n")
    _write(routes, "_helpers.py", "x = 1\n")  # underscore file, ignored
    _write(routes, "_lib/util.py", "x = 1\n")  # underscore folder, ignored
    found = discover(routes)
    assert len(found.routes) == 1


def test_method_conflict_caught_at_boot(tmp_path: Path) -> None:
    routes = tmp_path / "routes"
    _write(
        routes,
        "(group-a)/users.py",
        "from causeway import get\n@get\nasync def a() -> dict: return {}\n",
    )
    _write(
        routes,
        "(group-b)/users.py",
        "from causeway import get\n@get\nasync def b() -> dict: return {}\n",
    )
    with pytest.raises(TypeError, match="two handlers"):
        discover(routes)


def test_scope_providers_compose_outer_to_inner(tmp_path: Path) -> None:
    routes = tmp_path / "routes"
    _write(
        routes,
        "_scope.py",
        "from causeway import provide\n@provide('db')\nasync def outer_db(): yield 'outer'\n",
    )
    _write(
        routes,
        "users/_scope.py",
        "from causeway import provide\n"
        "@provide('db')\nasync def inner_db(): yield 'inner'\n"
        "@provide('cache')\nasync def cache(): yield 'cache'\n",
    )
    _write(
        routes,
        "users/index.py",
        "from causeway import get\n@get\nasync def r() -> dict: return {}\n",
    )
    _write(routes, "index.py", "from causeway import get\n@get\nasync def r() -> dict: return {}\n")

    found = discover(routes)
    by_path = {r.path: r for r in found.routes}

    # Root sees only outer provider.
    assert set(by_path["/"].providers) == {"db"}
    assert by_path["/"].providers["db"].__name__ == "outer_db"

    # /users sees inner db (override) + cache (added) — inner-most wins.
    assert set(by_path["/users"].providers) == {"db", "cache"}
    assert by_path["/users"].providers["db"].__name__ == "inner_db"


def test_scope_dup_provider_name_errors(tmp_path: Path) -> None:
    routes = tmp_path / "routes"
    _write(
        routes,
        "_scope.py",
        "from causeway import provide\n"
        "@provide('db')\nasync def a(): yield 1\n"
        "@provide('db')\nasync def b(): yield 2\n",
    )
    _write(routes, "index.py", "from causeway import get\n@get\nasync def r() -> dict: return {}\n")
    with pytest.raises(TypeError, match="two providers"):
        discover(routes)


def test_middleware_must_be_middleware_or_guard(tmp_path: Path) -> None:
    routes = tmp_path / "routes"
    _write(routes, "_middleware.py", "middleware = ['not a middleware']\n")
    _write(routes, "index.py", "from causeway import get\n@get\nasync def r() -> dict: return {}\n")
    with pytest.raises(TypeError, match="Middleware instance or a @guard"):
        discover(routes)


def test_guards_accepted(tmp_path: Path) -> None:
    routes = tmp_path / "routes"
    _write(
        routes,
        "_middleware.py",
        "from causeway import guard\n@guard\nasync def g(req): pass\nmiddleware = [g]\n",
    )
    _write(routes, "index.py", "from causeway import get\n@get\nasync def r() -> dict: return {}\n")
    found = discover(routes)
    assert len(found.routes[0].middleware) == 1


def test_get_post_both_on_same_function_errors() -> None:
    with pytest.raises(TypeError, match="decorated with both"):

        @causeway.post
        @causeway.get
        async def show() -> dict:
            return {}


def test_missing_routes_root() -> None:
    with pytest.raises(FileNotFoundError):
        discover("/does/not/exist")
