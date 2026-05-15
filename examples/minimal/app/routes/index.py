"""Root route — `GET /`."""

from __future__ import annotations

from msgspec import Struct

from quay import get


class Hello(Struct):
    message: str


@get
async def root() -> Hello:
    return Hello(message="hello from quay")
