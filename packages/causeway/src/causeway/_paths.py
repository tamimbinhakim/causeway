from __future__ import annotations

import re
from pathlib import PurePosixPath

_GROUP = re.compile(r"^\([^)]+\)$")
_DYNAMIC = re.compile(r"^\$([A-Za-z_][A-Za-z0-9_]*)$")
_CATCHALL = re.compile(r"^\$\$(.+)$")
_LEAF_TOKEN = re.compile(r"\([^)]*\)|[^.]+")


def url_for(rel_path: PurePosixPath) -> str:
    if rel_path.suffix != ".py":
        msg = f"route file must end in .py: {rel_path}"
        raise ValueError(msg)
    parts = list(rel_path.with_suffix("").parts)
    leaf = parts.pop()

    segments: list[str] = []
    for part in parts:
        if _GROUP.match(part):
            continue
        segments.extend(_folder_segments(part))

    leaf_pieces = _LEAF_TOKEN.findall(leaf)
    if leaf_pieces and leaf_pieces[-1] == "index":
        leaf_pieces.pop()
    for piece in leaf_pieces:
        if _GROUP.match(piece):
            continue
        segments.append(_leaf_segment(piece))

    if not segments:
        return "/"
    return "/" + "/".join(segments)


def _folder_segments(part: str) -> list[str]:
    pieces = _LEAF_TOKEN.findall(part)
    return [_leaf_segment(piece) for piece in pieces if not _GROUP.match(piece)]


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
