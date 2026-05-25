"""Smart dev reload classification."""

from __future__ import annotations

from pathlib import Path

from causeway.dev import classify_changes


def test_route_file_change_hot_reloads(tmp_path: Path) -> None:
    routes = tmp_path / "app" / "routes"
    route = routes / "users" / "$id.py"
    route.parent.mkdir(parents=True)
    route.write_text("from causeway import get\n@get\nasync def show(): ...\n")

    decision = classify_changes([route], routes_root=routes)

    assert decision.reload is True


def test_non_route_python_change_requires_restart(tmp_path: Path) -> None:
    routes = tmp_path / "app" / "routes"
    routes.mkdir(parents=True)
    plugins = tmp_path / "app" / "plugins.py"
    plugins.write_text("")

    decision = classify_changes([plugins], routes_root=routes)

    assert decision.reload is False
    assert "non-route" in (decision.reason or "")


def test_scope_lifecycle_change_requires_restart(tmp_path: Path) -> None:
    routes = tmp_path / "app" / "routes"
    routes.mkdir(parents=True)
    scope = routes / "_scope.py"
    scope.write_text("async def startup():\n    pass\n")

    decision = classify_changes([scope], routes_root=routes)

    assert decision.reload is False
    assert "startup" in (decision.reason or "")
