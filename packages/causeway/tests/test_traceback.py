"""Compact traceback formatter + ExceptionShield ASGI wrapper."""

from __future__ import annotations

import logging
from typing import Any

import pytest
from rich.console import Console

from causeway._traceback import (
    ExceptionShield,
    build_exception_panel,
    hint_for,
    log_exception,
    render_exception,
    root_cause,
)


def _wrap(outer: type[BaseException], inner: BaseException, msg: str = "outer") -> BaseException:
    try:
        raise inner
    except BaseException as e:
        try:
            raise outer(msg) from e
        except BaseException as wrapped:
            return wrapped


def _capture_panel(exc: BaseException, **kwargs: Any) -> str:
    console = Console(record=True, width=120, force_terminal=False, color_system=None)
    console.print(build_exception_panel(exc, **kwargs))
    return console.export_text()


# --- root_cause -------------------------------------------------------------


def test_root_cause_unwraps_explicit_chain() -> None:
    wrapped = _wrap(RuntimeError, ConnectionError("redis down"))
    assert isinstance(root_cause(wrapped), ConnectionError)
    assert str(root_cause(wrapped)) == "redis down"


def _make_suppressed() -> BaseException:
    try:
        try:
            raise ValueError("inner")
        except ValueError:
            raise RuntimeError("outer") from None
    except RuntimeError as exc:
        return exc
    raise AssertionError("unreachable")  # pragma: no cover


def _make_implicit() -> BaseException:
    try:
        try:
            raise ValueError("inner")
        except ValueError:
            raise RuntimeError("outer")  # noqa: B904 — intentional implicit chain
    except RuntimeError as exc:
        return exc
    raise AssertionError("unreachable")  # pragma: no cover


def test_root_cause_skips_suppressed_context() -> None:
    exc = _make_suppressed()
    # __cause__ suppressed via `from None`; root is the outer itself.
    assert root_cause(exc) is exc


def test_root_cause_follows_implicit_context() -> None:
    exc = _make_implicit()
    assert isinstance(root_cause(exc), ValueError)


def test_root_cause_unwraps_exception_group() -> None:
    inner = ConnectionError("redis down")
    group = ExceptionGroup("task group", [inner])
    assert root_cause(group) is inner


def test_root_cause_terminates_on_cycle() -> None:
    a = RuntimeError("a")
    b = RuntimeError("b")
    a.__cause__ = b
    b.__cause__ = a
    # Should not infinite-loop and should return one of the two.
    result = root_cause(a)
    assert result in (a, b)


# --- hint_for ---------------------------------------------------------------


def test_hint_for_redis_signature() -> None:
    msg = "Connect call failed ('127.0.0.1', 6379) connecting to localhost:6379."
    hint = hint_for(ConnectionError(msg))
    assert hint is not None
    assert "Redis" in hint


def test_hint_for_postgres_signature() -> None:
    hint = hint_for(ConnectionError("connection refused on port 5432"))
    assert hint is not None
    assert "Postgres" in hint


def test_hint_for_module_not_found_suggests_uv_add() -> None:
    hint = hint_for(ModuleNotFoundError(name="rich"))
    assert hint is not None
    assert "uv add rich" in hint or "uv add 'rich'" in hint


def test_hint_for_unknown_returns_none() -> None:
    assert hint_for(RuntimeError("totally unrelated")) is None


# --- build_exception_panel (rich) -------------------------------------------


def test_panel_renders_type_message_and_hint() -> None:
    text = _capture_panel(ConnectionError("Connect call failed connecting to localhost:6379."))
    assert "ConnectionError" in text
    assert "Redis is unreachable" in text
    assert "full traceback" in text


def test_panel_renders_request_metadata() -> None:
    class _URL:
        path = "/x"

    class _Req:
        method = "GET"
        url = _URL()

    text = _capture_panel(RuntimeError("oh no"), request=_Req(), request_id="rid")
    assert "request" in text
    assert "GET /x" in text
    assert "rid" in text


def test_panel_renders_group_count() -> None:
    group = ExceptionGroup("tg", [RuntimeError("a"), RuntimeError("b")])
    text = _capture_panel(group)
    assert "ExceptionGroup" in text
    assert "2 sub-exception" in text


def test_render_exception_caps_width_for_prefixed_dev_logs() -> None:
    console = Console(record=True, width=180, force_terminal=False, color_system=None)
    render_exception(RuntimeError("x" * 260), console=console)
    lines = console.export_text().splitlines()
    assert max(len(line) for line in lines) == 100


# --- log_exception ----------------------------------------------------------


def test_log_exception_honors_full_traceback_env(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("CAUSEWAY_FULL_TRACEBACK", "1")
    logger = logging.getLogger("causeway.test.full_traceback")
    logger.propagate = True
    try:
        raise RuntimeError("boom")
    except RuntimeError as exc:
        with caplog.at_level(logging.ERROR, logger=logger.name):
            log_exception(logger, exc, message="unhandled")
    assert any("unhandled" in record.getMessage() for record in caplog.records)
    assert any(record.exc_info for record in caplog.records)


# --- ExceptionShield --------------------------------------------------------


async def _drain_send() -> tuple[list[dict[str, Any]], Any]:
    received: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        received.append(message)

    return received, send


async def _noop_receive() -> dict[str, Any]:
    return {"type": "http.disconnect"}


async def test_shield_passes_through_success() -> None:
    async def app(scope: Any, receive: Any, send: Any) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    shield = ExceptionShield(app)
    received, send = await _drain_send()
    await shield({"type": "http"}, _noop_receive, send)
    assert received[0]["status"] == 200
    assert received[1]["body"] == b"ok"


async def test_shield_swallows_exception_after_response_started() -> None:
    async def app(scope: Any, receive: Any, send: Any) -> None:
        await send({"type": "http.response.start", "status": 500, "headers": []})
        await send({"type": "http.response.body", "body": b"already-sent"})
        raise RuntimeError("re-raised after response")

    shield = ExceptionShield(app)
    received, send = await _drain_send()
    await shield({"type": "http"}, _noop_receive, send)  # must not raise
    assert received[-1]["body"] == b"already-sent"


async def test_shield_writes_fallback_when_no_response_yet(
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def app(scope: Any, receive: Any, send: Any) -> None:
        raise RuntimeError("nothing sent yet")

    shield = ExceptionShield(app)
    received, send = await _drain_send()
    with caplog.at_level(logging.ERROR):
        await shield({"type": "http"}, _noop_receive, send)
    assert received[0]["type"] == "http.response.start"
    assert received[0]["status"] == 500
    assert b"internal server error" in received[1]["body"]


async def test_shield_passes_through_non_http_scopes() -> None:
    seen: list[str] = []

    async def app(scope: Any, receive: Any, send: Any) -> None:
        seen.append(scope["type"])

    shield = ExceptionShield(app)
    _, send = await _drain_send()
    await shield({"type": "lifespan"}, _noop_receive, send)
    assert seen == ["lifespan"]


# --- end-to-end integration -------------------------------------------------


async def test_middleware_exception_yields_500_without_propagating(
    tmp_path: Any, caplog: pytest.LogCaptureFixture
) -> None:
    """User's reported scenario: a custom middleware raises ConnectionError;
    Starlette renders the 500 via error_renderer, ServerErrorMiddleware
    re-raises, and the shield swallows so nothing escapes the ASGI app.
    """
    import httpx

    from causeway import create_app

    routes = tmp_path / "routes"
    (routes / "_middleware.py").parent.mkdir(parents=True, exist_ok=True)
    (routes / "_middleware.py").write_text(
        """from causeway import Middleware

class BoomMiddleware(Middleware):
    async def __call__(self, req, call_next):
        raise ConnectionError(
            "Error Multiple exceptions: [Errno 61] Connect call failed "
            "('127.0.0.1', 6379) connecting to localhost:6379."
        )

middleware = [BoomMiddleware()]
""",
    )
    (routes / "index.py").write_text(
        "from causeway import get\n@get\nasync def r() -> dict: return {'ok': True}\n",
    )

    app = create_app(routes)
    transport = httpx.ASGITransport(app=app)
    with caplog.at_level(logging.ERROR):
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
            resp = await client.get("/")

    assert resp.status_code == 500
    assert resp.headers["content-type"].startswith("application/problem+json")
    assert resp.json()["title"] == "internal"
    # The shield must have swallowed the re-raise; no ExceptionGroup or
    # raw ConnectionError trace should escape into the test runtime.
    assert any("ConnectionError" in r.getMessage() for r in caplog.records)
