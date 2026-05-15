"""`GET /users` (list) and `POST /users` (create)."""

from __future__ import annotations

from msgspec import Struct

from causeway import get, post, raises
from causeway.errors import BadRequest

from app.store import User, all_users, create_user


class NewUser(Struct):
    name: str
    email: str


@get
async def list_users() -> list[User]:
    return all_users()


@post
@raises(BadRequest)
async def create(data: NewUser) -> User:
    if not data.name or not data.email:
        raise BadRequest("name and email are required")
    return create_user(name=data.name, email=data.email)
