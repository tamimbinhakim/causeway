"""Smoke test using the *external* pattern, for contrast.

The bulk of this app's tests live inline in `app/routes/users/index.py`
and `app/routes/users/[id].py` under `if __name__ == "__causeway_test__":`.
Keep one external test here to show the escape hatch — useful when a
test needs to span multiple route files or model real client flows.
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
        body = created.json()
        assert body["ok"] is True
        user_id = body["data"]["id"]

        fetched = await c.get(f"/users/{user_id}")
        assert fetched.json()["data"]["email"] == "a@x"

        deleted = await c.delete(f"/users/{user_id}")
        assert deleted.json() == {"ok": True, "data": {"deleted": True}}
