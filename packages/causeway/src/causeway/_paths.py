from __future__ import annotations

import re
from pathlib import PurePosixPath

_FOLDER_DYNAMIC = re.compile(r"^\[([^.\]][^\]]*)\]$")
_FOLDER_CATCHALL = re.compile(r"^\[\.\.\.(.+)\]$")
_GROUP = re.compile(r"^\([^)]+\)$")
_LEAF_DYNAMIC = re.compile(r"^\$([A-Za-z_][A-Za-z0-9_]*)$")
_LEAF_CATCHALL = re.compile(r"^\$\$(.+)$")
_LEAF_TOKEN = re.compile(r"\[[^\]]*\]|\([^)]*\)|[^.]+")


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
        segments.append(_folder_segment(part))

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


def _folder_segment(part: str) -> str:
    if _FOLDER_CATCHALL.match(part):
        msg = "catch-all segments ([...rest]) are reserved for v0.2+"
        raise NotImplementedError(msg)
    m = _FOLDER_DYNAMIC.match(part)
    if m:
        return "{" + m.group(1) + "}"
    if part.startswith("_"):
        msg = f"private file leaked into URL translation: {part!r}"
        raise ValueError(msg)
    return part


def _leaf_segment(piece: str) -> str:
    if _LEAF_CATCHALL.match(piece):
        msg = "catch-all segments ($$rest) are reserved for v0.2+"
        raise NotImplementedError(msg)
    m = _LEAF_DYNAMIC.match(piece)
    if m:
        return "{" + m.group(1) + "}"
    if _FOLDER_CATCHALL.match(piece):
        msg = "catch-all segments ([...rest]) are reserved for v0.2+"
        raise NotImplementedError(msg)
    bracket = _FOLDER_DYNAMIC.match(piece)
    if bracket:
        return "{" + bracket.group(1) + "}"
    if piece.startswith("_"):
        msg = f"private file leaked into URL translation: {piece!r}"
        raise ValueError(msg)
    return piece
