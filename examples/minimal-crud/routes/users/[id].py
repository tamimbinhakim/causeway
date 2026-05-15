"""Read a user by id."""

from __future__ import annotations

from msgspec import Struct

from quay import get, raises
from quay.errors import NotFound


class User(Struct):
    id: str
    name: str


_USERS: dict[str, User] = {"u1": User(id="u1", name="ada")}


@get
@raises(NotFound)
async def show(id: str) -> User:
    user = _USERS.get(id)
    if user is None:
        raise NotFound(f"user {id} not found")
    return user
