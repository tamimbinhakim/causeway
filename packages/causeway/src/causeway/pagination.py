"""Cursor pagination primitives.

The framework commits to one shape: ``{items, next_cursor}`` with the cursor
as an opaque URL-safe base64 string. Handlers decode/encode payloads via
:meth:`Cursor.decode` / :meth:`Cursor.encode`; everything else stays standard
msgspec on the wire.

``next_cursor`` is a plain string (or ``None`` on the last page) rather than
a wrapped struct so the TS client gets ``next_cursor: string | null`` without
needing generic-aware codegen.
"""

from __future__ import annotations

import base64
import binascii
from typing import Any, Generic, TypeVar

import msgspec

from causeway.errors import BadRequest

T = TypeVar("T")


class Cursor:
    """Helpers for encoding/decoding opaque pagination tokens.

    Tokens are URL-safe base64 of a JSON dict. Handlers stay agnostic of the
    encoding — they only see the dict payload they put in.
    """

    __slots__ = ()

    @staticmethod
    def encode(payload: dict[str, Any]) -> str:
        """Turn a payload dict into an opaque token suitable for the wire."""
        raw = msgspec.json.encode(payload)
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    @staticmethod
    def decode(token: str | None) -> dict[str, Any]:
        """Reverse of :meth:`encode`. ``None`` and ``""`` both decode to ``{}``.

        Raises :class:`~causeway.errors.BadRequest` on a malformed token — the
        client got back a bad URL, that's a 400, not a 500.
        """
        if not token:
            return {}
        # encode() strips '=' padding for URL friendliness; restore it.
        padded = token + "=" * (-len(token) % 4)
        try:
            raw = base64.urlsafe_b64decode(padded.encode("ascii"))
            decoded = msgspec.json.decode(raw)
        except (binascii.Error, ValueError, msgspec.DecodeError, UnicodeDecodeError):
            raise BadRequest("invalid cursor token") from None
        if not isinstance(decoded, dict):
            raise BadRequest("invalid cursor token")
        return decoded


class Paginated(msgspec.Struct, Generic[T]):
    """A single page of results plus the cursor for the next one.

    ``next_cursor=None`` is the explicit end-of-pages signal — don't conflate
    with an empty ``items`` list (a filter that returns nothing on page 1 is
    ``Paginated(items=[], next_cursor=None)``).
    """

    items: list[T]
    next_cursor: str | None = None


__all__ = ["Cursor", "Paginated"]
