"""Runtime helpers used inside the AOT-compiled binary. Kept tiny on purpose."""

from __future__ import annotations

import hashlib
import inspect
import json
import sys
from pathlib import Path
from types import ModuleType


class FrozenIntegrityError(RuntimeError):
    """Raised when a frozen module's hash doesn't match its manifest entry."""


def verify_integrity(
    manifest_path: Path,
    routes_module: ModuleType,
    plugins_module: ModuleType,
) -> None:
    """Defense in depth against PYTHONPATH-shadowing of the frozen modules.

    Cosign signs the binary blob; this catches the narrower case where
    someone drops a fake `_frozen_plugins.py` next to the binary and
    relies on Python's import order to load it. Missing manifest = test
    run, skip silently.
    """
    if not manifest_path.is_file():
        return
    manifest = json.loads(manifest_path.read_text())
    pairs = ((routes_module, "routes_hash"), (plugins_module, "plugins_hash"))
    for module, key in pairs:
        expected = manifest.get(key)
        if expected is None:
            continue
        try:
            src = inspect.getsource(module).encode("utf-8")
        except (OSError, TypeError) as exc:
            raise FrozenIntegrityError(
                f"could not read source of {module.__name__} for integrity check",
            ) from exc
        actual = hashlib.sha256(src).hexdigest()
        if actual != expected:
            msg = (
                f"frozen-module integrity check failed for {module.__name__}: "
                f"manifest expected {expected[:12]}..., source hashes to {actual[:12]}..."
            )
            sys.stderr.write(f"causeway: {msg}\n")
            raise FrozenIntegrityError(msg)


__all__ = ["FrozenIntegrityError", "verify_integrity"]
