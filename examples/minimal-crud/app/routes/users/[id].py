"""`GET`/`PATCH`/`DELETE` on `/users/{id}`."""

from __future__ import annotations

from msgspec import Struct

from quay import delete, get, patch, raises
from quay.errors import NotFound

from app.store import User, delete_user, get_user, update_user


class UserPatch(Struct):
    name: str | None = None
    email: str | None = None


@get
@raises(NotFound)
async def show(id: int) -> User:
    user = get_user(id)
    if user is None:
        raise NotFound(f"user {id} not found")
    return user


@patch
@raises(NotFound)
async def edit(id: int, data: UserPatch) -> User:
    updated = update_user(id, name=data.name, email=data.email)
    if updated is None:
        raise NotFound(f"user {id} not found")
    return updated


@delete
@raises(NotFound)
async def remove(id: int) -> dict[str, bool]:
    if not delete_user(id):
        raise NotFound(f"user {id} not found")
    return {"deleted": True}
