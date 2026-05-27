"""SSE id/retry framing + Last-Event-Id resume cursor surfaces to handler."""

# pyright: basic

from __future__ import annotations

from typing import Annotated

import msgspec
from starlette.testclient import TestClient

from causeway._runtime import App, Context, SsePayload, stream
from causeway._runtime.params import Header
from causeway._runtime.streaming import encode_frame


class Tick(msgspec.Struct, tag_field="kind", tag="tick"):
    n: int


def test_encode_frame_plain_value() -> None:
    frame = encode_frame(Tick(n=1))
    assert frame.startswith(b"data: ")
    assert frame.endswith(b"\n\n")
    assert b"id:" not in frame
    assert b"retry:" not in frame


def test_encode_frame_with_sse_payload() -> None:
    frame = encode_frame(SsePayload(data=Tick(n=2), id="evt-42", retry_ms=2500))
    assert b"id: evt-42\n" in frame
    assert b"retry: 2500\n" in frame
    assert b"data: " in frame


def test_handler_reads_last_event_id_from_request() -> None:
    seen: dict[str, str | None] = {}
    app = App()

    @app.get("/feed")
    async def feed(
        ctx: Context,
        last_event_id: Annotated[str | None, Header("Last-Event-Id")] = None,
    ) -> stream[Tick]:
        seen["resume_from"] = last_event_id
        del ctx
        yield Tick(n=1)

    # Fresh connection: no header
    r = TestClient(app).get("/feed")
    assert r.status_code == 200
    assert seen["resume_from"] is None

    # Reconnect: header carries the last id the client saw
    r2 = TestClient(app).get("/feed", headers={"Last-Event-Id": "evt-42"})
    assert r2.status_code == 200
    assert seen["resume_from"] == "evt-42"


def test_full_handler_yields_sse_payload_with_id() -> None:
    app = App()

    @app.get("/feed")
    async def feed() -> stream[Tick]:
        # Runtime allows yielding bare T *or* SsePayload[T]; the static
        # annotation describes the data shape, the wire wrapper is opt-in.
        yield SsePayload(data=Tick(n=1), id="1", retry_ms=500)  # pyright: ignore[reportReturnType]
        yield SsePayload(data=Tick(n=2), id="2")  # pyright: ignore[reportReturnType]

    body = TestClient(app).get("/feed").text
    assert "id: 1\n" in body
    assert "id: 2\n" in body
    assert "retry: 500\n" in body
