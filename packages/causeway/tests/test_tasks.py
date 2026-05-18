"""Background-task contract tests using the in-memory adapter."""

from __future__ import annotations

import asyncio
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

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


# ---- typed-arg coercion -----------------------------------------------------


async def test_uuid_arg_survives_round_trip(adapter: InMemoryAdapter) -> None:
    """``enqueue(UUID(...))`` and ``async def handler(id: UUID)`` both work."""

    received: list[Any] = []

    @task()
    async def process(customer_id: UUID) -> None:
        received.append(customer_id)

    cid = uuid4()
    async with tasks_eager():
        await process.enqueue(cid)

    assert len(received) == 1
    assert isinstance(received[0], UUID)
    assert received[0] == cid


async def test_datetime_and_decimal_coerce(adapter: InMemoryAdapter) -> None:
    received: list[Any] = []

    @task()
    async def charge(when: datetime, amount: Decimal) -> None:
        received.append((when, amount))

    now = datetime(2026, 1, 2, 3, 4, 5)
    amount = Decimal("123.45")
    async with tasks_eager():
        await charge.enqueue(now, amount)

    assert received == [(now, amount)]


async def test_date_coerces_separately_from_datetime(
    adapter: InMemoryAdapter,
) -> None:
    received: list[Any] = []

    @task()
    async def expire(on: date) -> None:
        received.append(on)

    async with tasks_eager():
        await expire.enqueue(date(2026, 5, 17))

    assert received == [date(2026, 5, 17)]
    assert not isinstance(received[0], datetime)


async def test_untyped_args_pass_through(adapter: InMemoryAdapter) -> None:
    """A task with no recognized annotations gets no wrapper — args arrive raw."""

    received: list[Any] = []

    @task()
    async def noop(payload: dict[str, Any]) -> None:
        received.append(payload)

    async with tasks_eager():
        await noop.enqueue({"k": "v"})

    assert received == [{"k": "v"}]


async def test_optional_arg_passes_none_through(adapter: InMemoryAdapter) -> None:
    received: list[Any] = []

    @task()
    async def maybe(id: UUID, hint: str | None = None) -> None:
        received.append((id, hint))

    cid = uuid4()
    async with tasks_eager():
        await maybe.enqueue(cid)
        await maybe.enqueue(cid, hint="x")

    assert received == [(cid, None), (cid, "x")]


async def test_string_arg_still_coerces_to_uuid(adapter: InMemoryAdapter) -> None:
    """Callers that pass ``str(uuid)`` (legacy code, queue replays) still work."""

    received: list[Any] = []

    @task()
    async def legacy(id: UUID) -> None:
        received.append(id)

    cid = uuid4()
    async with tasks_eager():
        await legacy.enqueue(str(cid))

    assert received == [cid]
    assert isinstance(received[0], UUID)


def test_unencodable_arg_raises_typeerror() -> None:
    """Unknown types surface as a clear ``TypeError`` from the encoder."""

    class CustomThing:
        pass

    @task()
    async def takes_thing(t: Any) -> None:
        pass

    # _encode is called inside .enqueue(); easier to assert by invoking it
    # directly with the same shape.
    from causeway.tasks import _encode

    with pytest.raises(TypeError, match="unencodable"):
        _encode((CustomThing(),), {})
