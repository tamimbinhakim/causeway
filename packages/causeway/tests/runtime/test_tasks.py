"""Task[T] + InMemoryBackend tests."""

# pyright: basic

from __future__ import annotations

import asyncio

import pytest

from causeway._runtime import InMemoryBackend


@pytest.mark.asyncio
async def test_enqueue_runs_and_succeeds() -> None:
    backend = InMemoryBackend()

    async def add(a: int, b: int) -> int:
        await asyncio.sleep(0)
        return a + b

    task_id = await backend.enqueue(add, 2, 3)
    # Wait for it to finish.
    for _ in range(50):
        state = await backend.status(task_id)
        if state.status == "succeeded":
            break
        await asyncio.sleep(0.01)
    state = await backend.status(task_id)
    assert state.status == "succeeded"
    assert state.result == 5


@pytest.mark.asyncio
async def test_stream_sees_full_lifecycle() -> None:
    backend = InMemoryBackend()

    async def slow() -> str:
        await asyncio.sleep(0.05)
        return "done"

    task_id = await backend.enqueue(slow)
    seen: list[str] = []
    async for state in backend.stream(task_id):
        seen.append(state.status)
        if state.status == "succeeded":
            break
    # At minimum we expect queued/running → succeeded.
    assert seen[-1] == "succeeded"
    assert "running" in seen or "queued" in seen


@pytest.mark.asyncio
async def test_failure_surfaces_error() -> None:
    backend = InMemoryBackend()

    async def boom() -> int:
        raise ValueError("nope")

    task_id = await backend.enqueue(boom)
    for _ in range(50):
        state = await backend.status(task_id)
        if state.status == "failed":
            break
        await asyncio.sleep(0.01)
    state = await backend.status(task_id)
    assert state.status == "failed"
    assert "nope" in (state.error or "")


@pytest.mark.asyncio
async def test_cancel_marks_cancelled() -> None:
    backend = InMemoryBackend()

    async def long() -> None:
        await asyncio.sleep(5)

    task_id = await backend.enqueue(long)
    await asyncio.sleep(0.01)
    await backend.cancel(task_id)
    for _ in range(50):
        state = await backend.status(task_id)
        if state.status == "cancelled":
            break
        await asyncio.sleep(0.01)
    assert (await backend.status(task_id)).status == "cancelled"
