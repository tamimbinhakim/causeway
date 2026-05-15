"""POST a new user."""

from __future__ import annotations

from msgspec import Struct

from quay import post


class NewUser(Struct):
    name: str


class User(Struct):
    id: str
    name: str


@post
async def create(data: NewUser) -> User:
    new_id = f"u{hash(data.name) & 0xFFFF}"
    return User(id=new_id, name=data.name)
