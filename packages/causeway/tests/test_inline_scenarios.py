"""Inline-scenario runtime tests.

These exercise `scenario`, `expect`, the `_It` proxy, and `Response`
directly — without going through pytest's collection machinery (that
lives in :mod:`test_pytest_plugin`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from causeway._testing.errors import ScenarioAssertionError
from causeway._testing.loader import load_under_test, unload
from causeway._testing.registry import Registry


def _write(root: Path, rel: str, body: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)
    return p


def _route_file(tmp_path: Path, body: str) -> tuple[Path, Path]:
    routes = tmp_path / "routes"
    file = _write(routes, "index.py", body)
    return routes, file


def _collect(file: Path, routes_root: Path) -> Registry:
    reg = Registry(route_file=file, routes_root=routes_root, mode="collect")
    name = f"__collect_{abs(hash(str(file)))}"
    try:
        load_under_test(file, registry=reg, module_name=name)
    finally:
        unload(name)
    return reg


def _execute(file: Path, routes_root: Path, *, index: int, label: str) -> None:
    reg = Registry(
        route_file=file,
        routes_root=routes_root,
        mode="execute",
        target_index=index,
        target_label=label,
    )
    name = f"__exec_{abs(hash((str(file), index)))}"
    try:
        load_under_test(file, registry=reg, module_name=name)
    finally:
        unload(name)


def test_collection_records_each_scenario(tmp_path: Path) -> None:
    routes, file = _route_file(
        tmp_path,
        """
from causeway import get

@get
async def root() -> dict:
    return {"ok": True}

if __name__ == "__causeway_test__":
    from causeway.testing import expect, scenario
    with scenario("a") as it:
        expect(it.get("/")).body.ok == True
    with scenario("b") as it:
        expect(it.get("/")).body.ok == True
""",
    )
    reg = _collect(file, routes)
    assert [s.label for s in reg.scenarios] == ["a", "b"]


def test_execute_runs_one_scenario_against_the_app(tmp_path: Path) -> None:
    routes, file = _route_file(
        tmp_path,
        """
from causeway import get

@get
async def root() -> dict:
    return {"ok": True}

if __name__ == "__causeway_test__":
    from causeway.testing import expect, scenario
    with scenario("ok") as it:
        expect(it.get("/")).body.ok == True
""",
    )
    _execute(file, routes, index=0, label="ok")


def test_failing_assertion_raises_scenario_error(tmp_path: Path) -> None:
    routes, file = _route_file(
        tmp_path,
        """
from causeway import get

@get
async def root() -> dict:
    return {"ok": False}

if __name__ == "__causeway_test__":
    from causeway.testing import expect, scenario
    with scenario("fails") as it:
        expect(it.get("/")).body.ok == True
""",
    )
    with pytest.raises(ScenarioAssertionError) as exc_info:
        _execute(file, routes, index=0, label="fails")
    err = exc_info.value
    assert err.scenario_label == "fails"
    assert err.route_file is not None
    assert err.path == ("body", "ok")


def test_no_scenarios_in_file_is_a_quiet_no_op(tmp_path: Path) -> None:
    routes, file = _route_file(
        tmp_path,
        """
from causeway import get

@get
async def root() -> dict:
    return {}
""",
    )
    reg = _collect(file, routes)
    assert reg.scenarios == []


def test_collection_skips_http_side_effects(tmp_path: Path) -> None:
    """During collection, `it.get(...)` returns a null response."""
    routes, file = _route_file(
        tmp_path,
        """
from causeway import get

@get
async def root() -> dict:
    return {"ok": True}

if __name__ == "__causeway_test__":
    from causeway.testing import expect, scenario
    with scenario("ok") as it:
        # Collection runs this; the HTTP call is a no-op so the
        # assertion below also short-circuits.
        resp = it.get("/")
        assert resp.status_code == 0
""",
    )
    reg = _collect(file, routes)
    assert len(reg.scenarios) == 1
