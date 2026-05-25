"""Tests for cursor pagination primitives."""

from __future__ import annotations

import msgspec
import pytest

from causeway.errors import BadRequest
from causeway.pagination import Cursor, Paginated


def test_encode_decode_roundtrip() -> None:
    token = Cursor.encode({"id": 42, "ts": "2026-01-01"})
    assert Cursor.decode(token) == {"id": 42, "ts": "2026-01-01"}


def test_empty_token_decodes_to_empty_dict() -> None:
    assert Cursor.decode(None) == {}
    assert Cursor.decode("") == {}


def test_invalid_token_raises_bad_request() -> None:
    with pytest.raises(BadRequest) as exc_info:
        Cursor.decode("not-valid-base64-!!!")
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True


def test_non_dict_payload_rejected() -> None:
    token = Cursor.encode({"id": 1})  # valid envelope
    # Hand-roll a token that decodes to a list, not a dict.
    import base64

    bad = base64.urlsafe_b64encode(b"[1, 2, 3]").rstrip(b"=").decode()
    with pytest.raises(BadRequest):
        Cursor.decode(bad)
    # sanity: the valid one still decodes
    assert Cursor.decode(token) == {"id": 1}


def test_paginated_serializes_with_string_cursor() -> None:
    class Item(msgspec.Struct):
        name: str

    page = Paginated[Item](items=[Item(name="a")], next_cursor="abc")
    wire = msgspec.json.decode(msgspec.json.encode(page))
    assert wire == {"items": [{"name": "a"}], "next_cursor": "abc"}


def test_paginated_end_of_pages() -> None:
    class Item(msgspec.Struct):
        name: str

    page = Paginated[Item](items=[], next_cursor=None)
    wire = msgspec.json.decode(msgspec.json.encode(page))
    assert wire == {"items": [], "next_cursor": None}
