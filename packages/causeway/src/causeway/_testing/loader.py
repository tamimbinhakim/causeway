"""Import a route file under ``__name__ = "__causeway_test__"``.

A separate module name keeps the inline-test import disjoint from the
production import of the same physical file (which uses
``_causeway_routes_*``); collection / execution scenarios therefore
never interact with handlers cached for live routing.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from causeway._testing.registry import Registry, set_registry


def load_under_test(
    file: Path, *, registry: Registry, module_name: str | None = None
) -> ModuleType:
    """Import ``file`` with ``__name__`` set so the guard block executes.

    The registry is published via the contextvar and also stashed on the
    module as ``__causeway_registry__`` so callers can recover it after
    the import completes.
    """
    resolved = file.resolve()
    label = (
        resolved.with_suffix("")
        .as_posix()
        .replace("/", "_")
        .replace("[", "_")
        .replace("]", "_")
    )
    name = module_name or f"__causeway_test_{label}"

    set_registry(registry)
    try:
        spec = importlib.util.spec_from_file_location(name, resolved)
        if spec is None or spec.loader is None:
            msg = f"could not build import spec for {resolved}"
            raise ImportError(msg)
        module = importlib.util.module_from_spec(spec)
        # Importlib's loader sanity-checks that module.__name__ matches the
        # spec's name, so we run the source ourselves with the swapped
        # ``__name__`` baked into the globals.
        source = resolved.read_text()
        code = compile(source, str(resolved), "exec")
        module.__dict__.update(
            {
                "__name__": "__causeway_test__",
                "__file__": str(resolved),
                "__loader__": spec.loader,
                "__spec__": spec,
                "__package__": spec.parent,
                "__causeway_registry__": registry,
            }
        )
        sys.modules[name] = module
        exec(code, module.__dict__)
        module.__dict__["__name__"] = name
    finally:
        set_registry(None)
    return module


def unload(module_name: str) -> None:
    sys.modules.pop(module_name, None)
