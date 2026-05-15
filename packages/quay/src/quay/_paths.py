"""URL-pattern translation from a route file's relative path.

Two file-naming styles, freely mixable in the same tree:

**Folder style** (Next.js / file-system convention)
- ``index.py`` → the folder URL itself.
- ``foo.py`` → ``/foo``.
- ``[id].py`` / ``[id]/`` → ``/{id}`` (dynamic segment).
- ``[...rest]`` is reserved; raises ``NotImplementedError`` for v0.1.
- ``(group)/`` folders are stripped (route group; not in URL).

**Dot-flat style** (TanStack Router convention)
- ``users.$id.index.py`` → ``/users/{id}`` — the leaf filename is split on
  ``.`` and each piece becomes a URL segment.
- ``$name`` is a dynamic segment (named).
- ``(group)`` as a dotted piece is stripped, same as a group folder.
- A trailing ``index`` piece means "match parent exactly" and is dropped.
- ``$$rest`` is reserved for catch-all (v0.2+), parallel to ``[...rest]``.

Mixing: ``api/v1.$version.posts.py`` (folder + dotted leaf) is fine —
the folder hierarchy and the dotted leaf concatenate.

Underscore-prefixed files / folders are private and never reach this function.
"""

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
    """Translate a route file's path (relative to ``routes/``) into a URL pattern.

    ``rel_path`` must be a path under the routes root, ending in ``.py``. Examples
    (paths are shown POSIX-style for clarity):

    >>> url_for(PurePosixPath("index.py"))
    '/'
    >>> url_for(PurePosixPath("users/index.py"))
    '/users'
    >>> url_for(PurePosixPath("users/[id].py"))
    '/users/{id}'
    >>> url_for(PurePosixPath("(admin)/stats.py"))
    '/stats'
    >>> url_for(PurePosixPath("users/[id]/posts.py"))
    '/users/{id}/posts'
    >>> url_for(PurePosixPath("users.$id.index.py"))
    '/users/{id}'
    >>> url_for(PurePosixPath("posts.$slug.py"))
    '/posts/{slug}'
    >>> url_for(PurePosixPath("api/v1.$version.posts.py"))
    '/api/v1/{version}/posts'
    """
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
