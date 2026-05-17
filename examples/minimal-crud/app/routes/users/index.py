"""`GET /users` (list) and `POST /users` (create)."""

from __future__ import annotations

from app.store import User, _users, all_users, create_user
from causeway import get, post, raises
from causeway.errors import BadRequest
from msgspec import Struct


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


if __name__ == "__causeway_test__":
    from causeway.testing import expect, scenario

    with scenario("lists empty when no users exist") as it:
        _users.clear()
        expect(it.get("/users")).body == []

    with scenario("creates and then lists the user") as it:
        _users.clear()
        created = it.post("/users", json={"name": "ada", "email": "a@x"})
        expect(created).body.ok == True  # noqa: E712 - DSL equality
        expect(created).body.data.name == "ada"
        expect(it.get("/users")).body[0]["name"] == "ada"

    with scenario("rejects blank fields") as it:
        _users.clear()
        resp = it.post("/users", json={"name": "", "email": ""})
        expect(resp).body.ok == False  # noqa: E712 - DSL equality
        expect(resp).body.error.kind == "BadRequest"
