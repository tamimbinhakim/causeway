"""``mount_task_routes`` end-to-end: submit / status / stream against InMemoryBackend."""

# pyright: basic

from __future__ import annotations

import asyncio
import json

import msgspec
from starlette.testclient import TestClient

from causeway._runtime import App, InMemoryBackend, mount_task_routes


class TranscribeInput(msgspec.Struct):
    audio_url: str


class Transcript(msgspec.Struct):
    text: str
    confidence: float


async def transcribe(payload: TranscribeInput) -> Transcript:
    await asyncio.sleep(0)
    return Transcript(text=f"transcript of {payload.audio_url}", confidence=0.95)


def test_submit_returns_task_id() -> None:
    app = App()
    backend = InMemoryBackend()
    mount_task_routes(app, "/transcribe", transcribe, backend=backend)

    client = TestClient(app)
    response = client.post("/transcribe", json={"audio_url": "https://example.com/a.mp3"})
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["task_id"], str)
    assert len(body["task_id"]) > 0


def test_status_round_trips_result() -> None:
    app = App()
    backend = InMemoryBackend()
    mount_task_routes(app, "/transcribe", transcribe, backend=backend)

    client = TestClient(app)
    task_id = client.post("/transcribe", json={"audio_url": "https://x"}).json()["task_id"]

    # Poll until finished; the in-memory backend runs the coroutine on the event loop,
    # so a couple of GETs is enough for a no-op handler.
    final = None
    for _ in range(20):
        body = client.get(f"/transcribe/{task_id}").json()
        if body["status"] in ("succeeded", "failed"):
            final = body
            break
    assert final is not None
    assert final["status"] == "succeeded"
    assert final["result"]["text"] == "transcript of https://x"
    assert final["result"]["confidence"] == 0.95


def test_stream_emits_terminal_state() -> None:
    app = App()
    backend = InMemoryBackend()
    mount_task_routes(app, "/transcribe", transcribe, backend=backend)

    client = TestClient(app)
    task_id = client.post("/transcribe", json={"audio_url": "https://y"}).json()["task_id"]

    with client.stream("GET", f"/transcribe/{task_id}/events") as resp:
        assert resp.status_code == 200
        statuses: list[str] = []
        result_seen = False
        for line in resp.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            payload = json.loads(line[len("data: ") :])
            if "status" in payload:
                statuses.append(payload["status"])
                if payload["status"] == "succeeded":
                    assert payload["result"]["text"] == "transcript of https://y"
                    result_seen = True
                    break
    assert result_seen
    assert "succeeded" in statuses


def test_status_unknown_task_id_422() -> None:
    app = App()
    backend = InMemoryBackend()
    mount_task_routes(app, "/transcribe", transcribe, backend=backend)

    client = TestClient(app)
    resp = client.get("/transcribe/does-not-exist")
    assert resp.status_code == 422
    body = resp.json()
    assert body["field"] == "task_id"
    assert body["value"] == "does-not-exist"


def test_handler_signature_drives_submit_inputs() -> None:
    """Submit route inherits the handler's parameter shape — bad body fails validation."""
    app = App()
    backend = InMemoryBackend()
    mount_task_routes(app, "/transcribe", transcribe, backend=backend)

    client = TestClient(app)
    # Missing required field on the payload struct.
    resp = client.post("/transcribe", json={})
    assert resp.status_code == 422
