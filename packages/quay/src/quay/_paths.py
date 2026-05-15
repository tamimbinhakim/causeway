"""URL-pattern translation from a route file's relative path.

Rules (mirrors ``docs/routing.md``):

- ``index.py`` → the folder URL itself.
- ``foo.py`` → ``/foo``.
- ``[id].py`` → ``/{id}`` (dynamic segment).
- ``[...rest].py`` is reserved; raised as ``NotImplementedError`` for v0.1.
- ``(group)/`` folders are stripped (route group; not in URL).
- Underscore-prefixed files / folders are private and never reach this function.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

_DYNAMIC = re.compile(r"^\[([^.\]][^\]]*)\]$")
_CATCHALL = re.compile(r"^\[\.\.\.(.+)\]$")
_GROUP = re.compile(r"^\([^)]+\)$")


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
        segments.append(_segment(part))
    if leaf != "index":
        segments.append(_segment(leaf))

    if not segments:
        return "/"
    return "/" + "/".join(segments)


def _segment(part: str) -> str:
    if _CATCHALL.match(part):
        msg = "catch-all segments ([...rest]) are reserved for v0.2+"
        raise NotImplementedError(msg)
    m = _DYNAMIC.match(part)
    if m:
        return "{" + m.group(1) + "}"
    if part.startswith("_"):
        msg = f"private file leaked into URL translation: {part!r}"
        raise ValueError(msg)
    return part
