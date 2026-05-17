"""Find route trees so the pytest plugin knows which files to scan."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path


def find_routes_roots(start: Path, explicit: list[Path] | None = None) -> list[Path]:
    """Return one or more routes-root directories.

    Lookup order:

    1. Explicit ``--causeway-routes=PATH`` options (already resolved).
    2. Sibling ``app/routes/`` under any directory containing a
       ``causeway.toml`` from ``start`` upward.
    3. The first ``app/routes`` directory found by a shallow walk.
    """
    if explicit:
        return [p.resolve() for p in explicit if p.is_dir()]

    found: list[Path] = []
    for parent in [start, *start.parents]:
        manifest = parent / "causeway.toml"
        if manifest.is_file():
            candidate = parent / "app" / "routes"
            if candidate.is_dir():
                found.append(candidate.resolve())
    if found:
        return found

    for candidate in _shallow_walk_for_routes(start, max_depth=4):
        found.append(candidate.resolve())
        break
    return found


def _shallow_walk_for_routes(start: Path, *, max_depth: int) -> Iterator[Path]:
    for depth in range(max_depth + 1):
        for path in _iter_at_depth(start, depth):
            if path.is_dir() and path.name == "routes" and path.parent.name == "app":
                yield path


def _iter_at_depth(root: Path, depth: int) -> Iterator[Path]:
    if depth == 0:
        yield root
        return
    pattern = "/".join(["*"] * depth)
    yield from root.glob(pattern)


def under_any(roots: list[Path], path: Path) -> bool:
    """Is ``path`` inside any of ``roots``?"""
    p = path.resolve()
    for root in roots:
        try:
            p.relative_to(root)
        except ValueError:
            continue
        return True
    return False
