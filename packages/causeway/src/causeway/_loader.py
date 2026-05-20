"""Shared file-path module loader for the routes and events discoverers.

Both ``causeway.routing`` and ``causeway.events`` walk a tree of ``.py``
files and import them by path. The cache must be process-wide so a scope
file imported from two subtrees resolves to the same module instance —
:func:`causeway.routing._bind_providers` compares provider identity, so
re-importing would silently break injection.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

_module_cache: dict[Path, Any] = {}


def import_path(file: Path, *, label_prefix: str = "_causeway") -> Any:
    """Load a Python file by path, cached by resolved physical path."""
    resolved = file.resolve()
    cached = _module_cache.get(resolved)
    if cached is not None:
        return cached
    label = file.with_suffix("").as_posix().replace("/", ".").replace("[", "_").replace("]", "_")
    module_name = f"{label_prefix}_{label}"
    spec = importlib.util.spec_from_file_location(module_name, file)
    if spec is None or spec.loader is None:
        msg = f"could not build import spec for {file}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get(module_name)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        if previous is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous
        raise
    _module_cache[resolved] = module
    return module


def reset_module_cache() -> None:
    """Drop the import cache. Hot-reload calls this between scans."""
    for module in _module_cache.values():
        sys.modules.pop(module.__name__, None)
    _module_cache.clear()


__all__ = ["import_path", "reset_module_cache"]
