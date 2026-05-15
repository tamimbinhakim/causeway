"""End-to-end smoke test for the CRUD example.

Handlers decorated with `@raises(...)` return dyadpy's Result envelope:
`{"ok": true, "data": ...}` on success, `{"ok": false, "error": {...}}` on
a declared error. Handlers without `@raises` return the bare value.
"""

from __future__ import annotations

from collections.abc import Iterator

import httpx
import pytest

from app.app import app
from app.store import _users


@pytest.fixture(autouse=True)
def _reset_store() -> Iterator[None]:
    _users.clear()
    yield
    _users.clear()


async def test_full_crud_cycle() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        empty = await c.get("/users")
        assert empty.status_code == 200
        assert empty.json() == []

        created = await c.post("/users", json={"name": "ada", "email": "a@x"})
        assert created.status_code == 200
        body = created.json()
        assert body["ok"] is True
        user = body["data"]
        assert user["name"] == "ada"
        user_id = user["id"]

        fetched = await c.get(f"/users/{user_id}")
        assert fetched.status_code == 200
        assert fetched.json()["data"]["email"] == "a@x"

        patched = await c.patch(
            f"/users/{user_id}",
            json={"name": "grace", "email": None},
        )
        assert patched.json()["data"]["name"] == "grace"

        deleted = await c.delete(f"/users/{user_id}")
        assert deleted.json() == {"ok": True, "data": {"deleted": True}}

        missing = await c.get(f"/users/{user_id}")
        assert missing.json()["ok"] is False
        assert missing.json()["error"]["kind"] == "NotFound"


async def test_create_rejects_blank_fields() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        resp = await c.post("/users", json={"name": "", "email": ""})
    body = resp.json()
    assert body["ok"] is False
    assert body["error"]["kind"] == "BadRequest"
