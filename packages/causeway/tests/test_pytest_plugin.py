"""Pytest plugin tests — collection, execution, reporting."""

from __future__ import annotations

import pytest

pytest_plugins = ["pytester"]


_ROUTE_FILE = '''\
"""GET /users"""
from causeway import get

@get
async def list_users() -> dict:
    return {"items": []}

if __name__ == "__causeway_test__":
    from causeway.testing import expect, scenario
    with scenario("lists empty") as it:
        expect(it.get("/")).body == {"items": []}
    with scenario("intentionally fails") as it:
        expect(it.get("/")).body == {"items": ["unexpected"]}
'''


_PYPROJECT = """
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
"""


def _setup_routes(pytester: pytest.Pytester) -> None:
    pytester.mkdir("app")
    (pytester.path / "app" / "routes").mkdir()
    (pytester.path / "app" / "routes" / "index.py").write_text(_ROUTE_FILE)
    (pytester.path / "causeway.toml").write_text("[app]\nname = 't'\n")
    pytester.makepyprojecttoml(_PYPROJECT)


def test_plugin_discovers_and_runs_scenarios(pytester: pytest.Pytester) -> None:
    _setup_routes(pytester)
    result = pytester.runpytest_subprocess("-v", "--causeway-routes", "app/routes")
    result.assert_outcomes(passed=1, failed=1)
    result.stdout.fnmatch_lines(
        ["*::lists empty PASSED*", "*::intentionally fails FAILED*"]
    )


def test_plugin_can_be_disabled(pytester: pytest.Pytester) -> None:
    _setup_routes(pytester)
    result = pytester.runpytest_subprocess("-v", "--causeway-no-inline")
    # No items collected from route files; suite is otherwise empty.
    result.assert_outcomes()


def test_plugin_no_scenarios_no_items(pytester: pytest.Pytester) -> None:
    (pytester.path / "app").mkdir()
    (pytester.path / "app" / "routes").mkdir()
    (pytester.path / "app" / "routes" / "index.py").write_text(
        "from causeway import get\n@get\nasync def r() -> dict: return {}\n"
    )
    (pytester.path / "causeway.toml").write_text("[app]\nname = 't'\n")
    pytester.makepyprojecttoml(_PYPROJECT)
    result = pytester.runpytest_subprocess("--causeway-routes", "app/routes")
    result.assert_outcomes()
