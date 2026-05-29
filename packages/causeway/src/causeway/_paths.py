from __future__ import annotations

import re
from pathlib import PurePosixPath

_GROUP = re.compile(r"^\([^)]+\)$")
_DYNAMIC = re.compile(r"^\$([A-Za-z_][A-Za-z0-9_]*)$")
_CATCHALL = re.compile(r"^\$\$(.+)$")
_PUBLIC_PARAM = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def url_for(rel_path: PurePosixPath) -> str:
    if rel_path.suffix != ".py":
        msg = f"route file must end in .py: {rel_path}"
        raise ValueError(msg)
    parts = list(rel_path.with_suffix("").parts)
    leaf = parts.pop()

    segments: list[str] = []
    for part in parts:
        _reject_dotted(part)
        if _GROUP.match(part):
            continue
        segments.append(_leaf_segment(part))

    _reject_dotted(leaf)
    if _GROUP.match(leaf):
        msg = f"route groups must be folders, not leaf files: {leaf!r}"
        raise ValueError(msg)
    if leaf != "index":
        segments.append(_leaf_segment(leaf))

    if not segments:
        return "/"
    return "/" + "/".join(segments)


def public_path_for(rel_path: PurePosixPath) -> str:
    """Return the client-facing route path, preserving ``$param`` syntax."""
    return _PUBLIC_PARAM.sub(r"$\1", url_for(rel_path))


def route_key_for(method: str, rel_path: PurePosixPath) -> str:
    return f"{method.upper()} {public_path_for(rel_path)}"


def route_key_from_url(method: str, path: str) -> str:
    public_path = _PUBLIC_PARAM.sub(r"$\1", path)
    return f"{method.upper()} {public_path}"


def scope_groups_for(rel_path: PurePosixPath) -> tuple[str, ...]:
    if rel_path.suffix != ".py":
        msg = f"route file must end in .py: {rel_path}"
        raise ValueError(msg)
    groups: list[str] = []
    parts = list(rel_path.with_suffix("").parts)
    leaf = parts.pop()
    for part in parts:
        _reject_dotted(part)
        groups.extend(_groups_in_piece(part))
    _reject_dotted(leaf)
    if _GROUP.match(leaf):
        msg = f"route groups must be folders, not leaf files: {leaf!r}"
        raise ValueError(msg)
    return tuple(groups)


def _groups_in_piece(piece: str) -> list[str]:
    return [piece[1:-1]] if _GROUP.match(piece) and len(piece) > 2 else []


def _reject_dotted(part: str) -> None:
    if "." in part:
        msg = f"dotted route files are not supported; use folders instead: {part!r}"
        raise ValueError(msg)


def _leaf_segment(piece: str) -> str:
    if _CATCHALL.match(piece):
        msg = "catch-all segments ($$rest) are reserved for v0.2+"
        raise NotImplementedError(msg)
    m = _DYNAMIC.match(piece)
    if m:
        return "{" + m.group(1) + "}"
    if piece.startswith("["):
        msg = f"bracket route params are not supported; use ${piece[1:-1]} instead"
        raise ValueError(msg)
    if piece.startswith("_"):
        msg = f"private file leaked into URL translation: {piece!r}"
        raise ValueError(msg)
    return piece
