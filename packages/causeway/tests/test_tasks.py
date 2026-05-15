"""Background-task contract tests using the in-memory adapter."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from causeway._cron import next_fire
from causeway.tasks import (
    InMemoryAdapter,
    TaskRef,
    _clear,
    cron,
    cron_jobs,
    registered_tasks,
    set_adapter,
    task,
    tasks_eager,
)


@pytest.fixture(autouse=True)
def _reset_registries() -> Any:
    _clear()
    yield
    _clear()


@pytest.fixture
async def adapter() -> Any:
    a = InMemoryAdapter()
    await a.startup(settings=None)
    set_adapter(a)
    yield a
    await a.shutdown()


async def test_task_decorator_returns_taskref() -> None:
    @task(queue="emails", retries=3, backoff="linear")
    async def send_welcome(user_id: str) -> str:
        return f"hi {user_id}"

    assert isinstance(send_welcome, TaskRef)
    assert send_welcome.queue == "emails"
    assert send_welcome.retries == 3
    assert send_welcome.backoff == "linear"

    snap = registered_tasks()
    assert any(r.name == "send_welcome" for r in snap.values())


async def test_enqueue_runs_inline_under_eager(adapter: InMemoryAdapter) -> None:
    calls: list[str] = []

    @task()
    async def record(payload: str) -> None:
        calls.append(payload)

    async with tasks_eager():
        task_id = await record.enqueue("hello")

    state = await adapter.status(task_id)
    assert state.state == "complete"
    assert calls == ["hello"]


async def test_enqueue_runs_async_without_eager(adapter: InMemoryAdapter) -> None:
    @task()
    async def echo(payload: str) -> str:
        await asyncio.sleep(0)
        return payload

    task_id = await echo.enqueue("hi")
    result = await adapter.result(task_id)
    assert result == "hi"


async def test_retries_then_succeeds(adapter: InMemoryAdapter) -> None:
    attempts: list[int] = []

    @task(retries=2, backoff="fixed")
    async def flaky() -> str:
        attempts.append(1)
        if len(attempts) < 3:
            raise RuntimeError("not yet")
        return "ok"

    task_id = await flaky.enqueue()
    result = await adapter.result(task_id)
    assert result == "ok"
    assert len(attempts) == 3


async def test_retries_exhausted(adapter: InMemoryAdapter) -> None:
    @task(retries=1, backoff="fixed")
    async def always_fails() -> None:
        raise RuntimeError("boom")

    task_id = await always_fails.enqueue()
    with pytest.raises(RuntimeError, match="boom"):
        await adapter.result(task_id)
    state = await adapter.status(task_id)
    assert state.state == "failed"


async def test_cron_decorator_records_expr() -> None:
    @cron("*/5 * * * *")
    async def hourly() -> None:
        pass

    pairs = cron_jobs()
    assert len(pairs) == 1
    ref, expr = pairs[0]
    assert ref.name == "hourly"
    assert expr == "*/5 * * * *"


async def test_status_unknown_task(adapter: InMemoryAdapter) -> None:
    state = await adapter.status("does-not-exist")
    assert state.state == "failed"
    assert state.error is not None


async def test_no_adapter_raises_clear_error() -> None:
    @task()
    async def t() -> None:
        pass

    from contextvars import copy_context

    ctx = copy_context()

    async def go() -> None:
        with pytest.raises(RuntimeError, match="No TaskAdapter"):
            await t.enqueue()

    await ctx.run(asyncio.create_task, go())  # type: ignore[misc]
    # Direct execution as a fallback path so the assertion is observed:
    # the above ctx.run schedules without awaiting properly across loops.
    # Verify by running ``go`` directly:
    await go()


def test_cron_parser_every_minute_yields_60s() -> None:
    from datetime import datetime as _dt

    delay = next_fire("* * * * *", _dt(2026, 1, 1, 12, 0, 0))
    assert delay == 60.0


def test_cron_parser_step_field() -> None:
    from datetime import datetime as _dt

    # */5 fires at 0, 5, 10, ... — from 12:01 the next is 12:05.
    delay = next_fire("*/5 * * * *", _dt(2026, 1, 1, 12, 1, 0))
    assert delay == 4 * 60.0
