"""Tests for permission expansion + the ``require_permission`` guard."""

from __future__ import annotations

from typing import Any, ClassVar

import pytest
from starlette.requests import Request

from causeway import errors, plugins
from causeway.auth import check_permission, expand_permissions, require_permission


def test_manage_expands_to_write_and_read() -> None:
    assert expand_permissions({"api_keys:manage"}) == {
        "api_keys:manage",
        "api_keys:write",
        "api_keys:read",
    }


def test_write_expands_to_read() -> None:
    assert expand_permissions({"posts:write"}) == {"posts:write", "posts:read"}


def test_read_does_not_expand() -> None:
    assert expand_permissions({"posts:read"}) == {"posts:read"}


def test_star_short_circuits() -> None:
    assert expand_permissions({"*", "posts:write"}) == {"*"}


def test_check_permission_star_wins() -> None:
    assert check_permission({"*"}, "anything:read") is True


def test_check_permission_explicit() -> None:
    assert check_permission({"posts:manage"}, "posts:read") is True
    assert check_permission({"posts:read"}, "posts:write") is False


def test_check_permission_unknown_domain() -> None:
    assert check_permission({"posts:read"}, "billing:read") is False


class _FakeAuth:
    """Minimal AuthProvider stub for testing the guard."""

    contract_version: ClassVar[str] = "v1.1"

    def __init__(self, user: Any | None, perms: set[str]) -> None:
        self._user = user
        self._perms = perms

    async def startup(self, settings: Any) -> None: ...
    async def shutdown(self) -> None: ...
    async def ready(self) -> bool:
        return True

    async def current_user(self, req: Any) -> Any | None:
        return self._user

    async def login(self, creds: dict[str, Any]) -> Any:
        return self._user

    async def logout(self, req: Any) -> None: ...
    async def verify(self, token: str) -> Any | None:
        return self._user

    async def has_permission(self, user: Any, perm: str) -> bool:
        return check_permission(self._perms, perm)


def _stub_request() -> Request:
    return Request({"type": "http", "headers": [], "method": "GET", "path": "/"})


@pytest.mark.asyncio
async def test_require_permission_passes_when_user_has_it() -> None:
    plugins.clear()
    plugins.register(_FakeAuth(user={"id": "u1"}, perms={"posts:manage"}))
    try:
        await require_permission("posts:read")(_stub_request())
    finally:
        plugins.clear()


@pytest.mark.asyncio
async def test_require_permission_forbids_when_user_lacks_it() -> None:
    plugins.clear()
    plugins.register(_FakeAuth(user={"id": "u1"}, perms={"posts:read"}))
    try:
        with pytest.raises(errors.Forbidden):
            await require_permission("posts:write")(_stub_request())
    finally:
        plugins.clear()


@pytest.mark.asyncio
async def test_require_permission_unauthorizes_anonymous() -> None:
    plugins.clear()
    plugins.register(_FakeAuth(user=None, perms=set()))
    try:
        with pytest.raises(errors.Unauthorized):
            await require_permission("posts:read")(_stub_request())
    finally:
        plugins.clear()
