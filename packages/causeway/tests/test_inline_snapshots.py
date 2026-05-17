"""Inline snapshot tests."""

from __future__ import annotations

import pytest

pytest_plugins = ["pytester"]


_PYPROJECT = """
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
"""


def _setup_route(pytester: pytest.Pytester, snapshot_arg: str) -> None:
    pytester.mkdir("app")
    (pytester.path / "app" / "routes").mkdir()
    (pytester.path / "app" / "routes" / "index.py").write_text(
        f'''\
"""GET /"""
from causeway import get

@get
async def root() -> dict:
    return {{"status": "ok", "count": 1}}

if __name__ == "__causeway_test__":
    from causeway.testing import expect, scenario, snapshot
    with scenario("matches snapshot") as it:
        expect(it.get("/")).body == snapshot({snapshot_arg})
'''
    )
    (pytester.path / "causeway.toml").write_text("[app]\nname = 't'\n")
    pytester.makepyprojecttoml(_PYPROJECT)


def test_matching_snapshot_passes(pytester: pytest.Pytester) -> None:
    _setup_route(pytester, '{"status": "ok", "count": 1}')
    result = pytester.runpytest_subprocess("--causeway-routes", "app/routes")
    result.assert_outcomes(passed=1)


def test_mismatching_snapshot_fails(pytester: pytest.Pytester) -> None:
    _setup_route(pytester, '{"status": "ok", "count": 99}')
    result = pytester.runpytest_subprocess("--causeway-routes", "app/routes")
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*snapshot mismatch*"])


def test_ellipsis_matches_any_leaf(pytester: pytest.Pytester) -> None:
    _setup_route(pytester, '{"status": "ok", "count": ...}')
    result = pytester.runpytest_subprocess("--causeway-routes", "app/routes")
    result.assert_outcomes(passed=1)


def test_empty_snapshot_fails_without_update_flag(pytester: pytest.Pytester) -> None:
    _setup_route(pytester, "")
    result = pytester.runpytest_subprocess("--causeway-routes", "app/routes")
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*rerun with*--update-snapshots*"])


def test_update_flag_records_value(pytester: pytest.Pytester) -> None:
    _setup_route(pytester, "")
    route_file = pytester.path / "app" / "routes" / "index.py"
    original = route_file.read_text()
    assert "snapshot()" in original
    result = pytester.runpytest_subprocess("--causeway-routes", "app/routes", "--update-snapshots")
    result.assert_outcomes(passed=1)
    updated = route_file.read_text()
    assert "snapshot()" not in updated
    assert "'status': 'ok'" in updated or '"status": "ok"' in updated
