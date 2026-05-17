"""Pytest plugin — collects and runs inline route scenarios.

Activated automatically via the ``pytest11`` entry point declared in
``pyproject.toml``. The plugin:

1. Adds CLI options for routes roots, snapshot updates, and a kill switch.
2. Registers a custom :class:`Collector` for any ``.py`` file under a
   detected routes root that has an ``if __name__ == "__causeway_test__":``
   guard.
3. Each scenario discovered becomes one ``pytest.Item`` whose ``runtest``
   re-imports the module in *execute* mode targeting that scenario.
4. At session end, applies any pending snapshot edits when
   ``--update-snapshots`` was passed.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from causeway._testing.discover import find_routes_roots, under_any
from causeway._testing.errors import ScenarioAssertionError
from causeway._testing.loader import load_under_test, unload
from causeway._testing.registry import Registry
from causeway._testing.rewrite import apply_edits
from causeway._testing.snapshot import _PENDING

if TYPE_CHECKING:
    from collections.abc import Iterator

GUARD = '__name__ == "__causeway_test__"'
GUARD_ALT = "__name__ == '__causeway_test__'"


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("causeway")
    group.addoption(
        "--causeway-routes",
        action="append",
        default=[],
        metavar="PATH",
        help="Routes-root directory to scan for inline scenarios. Repeatable.",
    )
    group.addoption(
        "--update-snapshots",
        action="store_true",
        default=False,
        help="Record or update inline snapshots in route files.",
    )
    group.addoption(
        "--causeway-no-inline",
        action="store_true",
        default=False,
        help="Disable inline-scenario collection entirely.",
    )


def pytest_configure(config: pytest.Config) -> None:
    raw = config.getoption("--causeway-routes") or []
    explicit = [Path(p) for p in raw]
    rootpath = Path(str(config.rootpath))
    roots = find_routes_roots(rootpath, explicit=explicit or None)
    config._causeway_routes_roots = roots  # type: ignore[attr-defined]
    config._causeway_update = bool(config.getoption("--update-snapshots"))  # type: ignore[attr-defined]
    config._causeway_disabled = bool(  # type: ignore[attr-defined]
        config.getoption("--causeway-no-inline")
    )


def pytest_collect_file(parent: pytest.Collector, file_path: Path) -> pytest.Collector | None:
    config = parent.config
    if getattr(config, "_causeway_disabled", False):
        return None
    if file_path.suffix != ".py":
        return None
    if file_path.name.startswith("_") or file_path.name.startswith("."):
        return None
    roots = getattr(config, "_causeway_routes_roots", []) or []
    if not roots or not under_any(roots, file_path):
        return None
    try:
        source = file_path.read_text()
    except OSError:
        return None
    if GUARD not in source and GUARD_ALT not in source:
        return None
    routes_root = _pick_root(roots, file_path)
    if routes_root is None:
        return None
    return RouteFileCollector.from_parent(parent, path=file_path, routes_root=routes_root)


def _pick_root(roots: list[Path], file_path: Path) -> Path | None:
    for root in roots:
        try:
            file_path.resolve().relative_to(root)
        except ValueError:
            continue
        return root
    return None


class RouteFileCollector(pytest.File):
    """Collects every ``scenario(...)`` block declared in a route file."""

    def __init__(self, *args: Any, routes_root: Path, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.routes_root = routes_root

    def collect(self) -> Iterator[pytest.Item]:
        registry = Registry(
            route_file=Path(str(self.path)),
            routes_root=self.routes_root,
            mode="collect",
            update_snapshots=False,
        )
        module_name = f"__causeway_collect_{abs(hash(str(self.path)))}"
        try:
            load_under_test(self.path, registry=registry, module_name=module_name)
        except Exception as exc:
            raise pytest.UsageError(
                f"failed to collect inline scenarios from {self.path}: {exc}"
            ) from exc
        finally:
            unload(module_name)

        for index, registered in enumerate(registry.scenarios):
            yield ScenarioItem.from_parent(
                self,
                name=registered.label,
                index=index,
                label=registered.label,
                lineno=registered.lineno,
                routes_root=self.routes_root,
            )


class ScenarioItem(pytest.Item):
    """One inline scenario, runnable via pytest."""

    def __init__(
        self,
        *args: Any,
        index: int,
        label: str,
        lineno: int,
        routes_root: Path,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.index = index
        self.label = label
        self.lineno = lineno
        self.routes_root = routes_root

    def runtest(self) -> None:
        config = self.config
        update = bool(getattr(config, "_causeway_update", False))
        registry = Registry(
            route_file=Path(str(self.path)),
            routes_root=self.routes_root,
            mode="execute",
            target_index=self.index,
            target_label=self.label,
            update_snapshots=update,
        )
        module_name = f"__causeway_exec_{abs(hash((str(self.path), self.index)))}"
        try:
            load_under_test(self.path, registry=registry, module_name=module_name)
        finally:
            unload(module_name)

    def repr_failure(
        self, excinfo: pytest.ExceptionInfo[BaseException], style: Any | None = None
    ) -> Any:
        exc = excinfo.value
        if isinstance(exc, ScenarioAssertionError):
            return str(exc)
        return super().repr_failure(excinfo, style=style)

    def reportinfo(self) -> tuple[Path, int, str]:
        return Path(str(self.path)), self.lineno - 1, f"scenario: {self.label}"


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    config = session.config
    if not getattr(config, "_causeway_update", False):
        if _PENDING:
            # Defensive: if anything queued without the flag, drop it.
            _PENDING.clear()
        return
    edits = list(_PENDING)
    _PENDING.clear()
    if not edits:
        return
    counts = apply_edits(edits)
    if counts:
        reporter = config.pluginmanager.get_plugin("terminalreporter")
        if reporter is not None:
            total = sum(counts.values())
            reporter.write_line(
                f"\ncauseway: updated {total} snapshot(s) across {len(counts)} file(s)"
            )
    _ = exitstatus
