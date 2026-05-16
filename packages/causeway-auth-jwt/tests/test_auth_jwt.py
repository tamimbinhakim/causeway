from __future__ import annotations

import types

import jwt
import pytest
from pydantic import SecretStr

import causeway.plugins as plugin_registry
from causeway_auth_jwt import JwtAuth, plugin


@pytest.fixture(autouse=True)
def _clear_registry() -> None:
    plugin_registry.clear()


def _req(authorization: str | None = None) -> types.SimpleNamespace:
    headers = {"authorization": authorization} if authorization is not None else {}
    return types.SimpleNamespace(headers=headers)


_SECRET = "test-secret-must-be-at-least-32-bytes-long-ok"


async def test_login_then_verify_roundtrip() -> None:
    auth = JwtAuth(secret=_SECRET)
    token = await auth.login({"sub": "ada", "scope": "read"})
    claims = await auth.verify(token)
    assert claims is not None
    assert claims["sub"] == "ada"
    assert claims["scope"] == "read"


async def test_verify_returns_none_on_bad_signature() -> None:
    auth = JwtAuth(secret=_SECRET)
    other = JwtAuth(secret=_SECRET+"x")
    token = await auth.login({"sub": "x"})
    assert await other.verify(token) is None


async def test_current_user_from_bearer_header() -> None:
    auth = JwtAuth(secret=_SECRET)
    token = await auth.login({"sub": "u1"})
    user = await auth.current_user(_req(f"Bearer {token}"))
    assert user is not None
    assert user["sub"] == "u1"


async def test_current_user_handles_case_insensitive_scheme() -> None:
    auth = JwtAuth(secret=_SECRET)
    token = await auth.login({"sub": "u1"})
    user = await auth.current_user(_req(f"bearer {token}"))
    assert user is not None


async def test_current_user_returns_none_without_bearer() -> None:
    auth = JwtAuth(secret=_SECRET)
    assert await auth.current_user(_req(None)) is None
    assert await auth.current_user(_req("")) is None
    assert await auth.current_user(_req("Basic abcd")) is None


async def test_current_user_returns_none_when_token_invalid() -> None:
    auth = JwtAuth(secret=_SECRET)
    assert await auth.current_user(_req("Bearer not-a-jwt")) is None


async def test_current_user_handles_request_without_headers() -> None:
    auth = JwtAuth(secret=_SECRET)

    class NoHeaders:
        pass

    assert await auth.current_user(NoHeaders()) is None


async def test_logout_is_a_no_op() -> None:
    await JwtAuth(secret=_SECRET).logout(_req("Bearer x"))


async def test_lifecycle_methods() -> None:
    auth = JwtAuth(secret=_SECRET)
    await auth.startup(None)
    await auth.shutdown()
    assert await auth.ready() is True


async def test_ready_false_without_secret() -> None:
    assert await JwtAuth(secret="").ready() is False


async def test_issuer_and_audience_are_enforced() -> None:
    auth = JwtAuth(secret=_SECRET, issuer="iss-a", audience="aud-a")

    # Token signed with mismatched issuer/audience must not verify.
    bad = jwt.encode(
        {"sub": "x", "iss": "iss-b", "aud": "aud-a"}, _SECRET, algorithm="HS256"
    )
    assert await auth.verify(bad) is None

    good = jwt.encode(
        {"sub": "x", "iss": "iss-a", "aud": "aud-a"}, _SECRET, algorithm="HS256"
    )
    assert await auth.verify(good) is not None


def test_plugin_no_op_without_secret() -> None:
    plugin(types.SimpleNamespace())
    assert plugin_registry.registered() == []


def test_plugin_registers_with_settings() -> None:
    plugin(types.SimpleNamespace(jwt_secret=_SECRET, jwt_algorithm="HS256"))
    [adapter] = plugin_registry.registered()
    assert isinstance(adapter, JwtAuth)
    assert adapter.secret == _SECRET


def test_plugin_unwraps_secret_str() -> None:
    plugin(types.SimpleNamespace(jwt_secret=SecretStr("hidden")))
    [adapter] = plugin_registry.registered()
    assert isinstance(adapter, JwtAuth)
    assert adapter.secret == "hidden"
