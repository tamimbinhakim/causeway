"""`GET`/`PATCH`/`DELETE` on `/users/{id}`."""

from __future__ import annotations

from app.store import User, _users, create_user, delete_user, get_user, update_user
from causeway import delete, get, patch, raises
from causeway.errors import NotFound
from msgspec import Struct


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


if __name__ == "__causeway_test__":
    from causeway.testing import expect, scenario

    with scenario("show returns 404 envelope when missing") as it:
        _users.clear()
        resp = it.get("/users/999")
        expect(resp).body.ok == False  # noqa: E712 - DSL equality
        expect(resp).body.error.kind == "NotFound"

    with scenario("edit renames an existing user") as it:
        _users.clear()
        user = create_user(name="ada", email="a@x")
        patched = it.patch(f"/users/{user.id}", json={"name": "grace", "email": None})
        expect(patched).body.data.name == "grace"
        expect(patched).body.data.email == "a@x"

    with scenario("delete removes the user") as it:
        _users.clear()
        user = create_user(name="ada", email="a@x")
        deleted = it.delete(f"/users/{user.id}")
        expect(deleted).body.data.deleted == True  # noqa: E712 - DSL equality
        expect(it.get(f"/users/{user.id}")).body.error.kind == "NotFound"
