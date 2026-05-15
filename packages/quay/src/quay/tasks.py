"""Background-task contract + decorator + reference adapter.

The framework owns the *what* (a callable with a payload schema, a queue,
a retry / backoff policy) and lets you plug in the *how* (Dramatiq, Celery,
Arq, in-process). This module ships the contract and one reference adapter
that runs jobs in-process — enough for tests and the dev loop.

Production deployments register a real adapter in ``src/app/plugins.py``::

    from quay import register
    from quay.tasks.dramatiq import DramatiqAdapter

    register(DramatiqAdapter(broker_url="redis://localhost"))
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar, Literal

_log = logging.getLogger("quay.tasks")

Backoff = Literal["fixed", "linear", "exponential"]


@dataclass(slots=True)
class TaskState:
    """Snapshot returned by ``adapter.status()``."""

    state: Literal["pending", "running", "complete", "failed"]
    result: Any = None
    error: str | None = None


@dataclass(slots=True)
class TaskRef:
    """Handle to a registered ``@task`` function.

    Adapters use ``module`` + ``name`` to identify a task on the wire so a
    queued job survives a process restart. The original callable is kept on
    the ref so the eager / in-process adapter can dispatch directly.
    """

    module: str
    name: str
    queue: str = "default"
    retries: int = 0
    backoff: Backoff = "exponential"
    fn: Callable[..., Awaitable[Any]] | None = None

    async def enqueue(self, *args: Any, **kwargs: Any) -> str:
        adapter = _active_adapter()
        payload = _encode(args, kwargs)
        return await adapter.enqueue(self, payload)

    async def schedule(self, when: datetime, *args: Any, **kwargs: Any) -> str:
        adapter = _active_adapter()
        payload = _encode(args, kwargs)
        return await adapter.schedule(self, when, payload)

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"TaskRef({self.module}.{self.name}, queue={self.queue!r})"


# Module-level registry of every ``@task`` discovered. Adapters can iterate
# this on startup to register cron jobs / declare workers.
_registered_tasks: dict[str, TaskRef] = {}
# Cron declarations: list of (task, cron_expr).
_cron_jobs: list[tuple[TaskRef, str]] = []


def task(
    *,
    queue: str = "default",
    retries: int = 0,
    backoff: Backoff = "exponential",
) -> Callable[[Callable[..., Awaitable[Any]]], TaskRef]:
    """Mark a coroutine as a background task.

    The decorator returns a :class:`TaskRef` — calling it directly raises,
    forcing users through ``.enqueue(...)``. That keeps the failure mode
    obvious: you can't accidentally execute a task in-band by forgetting
    the ``.enqueue``.
    """

    def decorator(fn: Callable[..., Awaitable[Any]]) -> TaskRef:
        ref = TaskRef(
            module=getattr(fn, "__module__", "?"),
            name=fn.__name__,
            queue=queue,
            retries=retries,
            backoff=backoff,
            fn=fn,
        )
        key = f"{ref.module}.{ref.name}"
        _registered_tasks[key] = ref
        return ref

    return decorator


def cron(expr: str) -> Callable[[Callable[..., Awaitable[Any]]], TaskRef]:
    """Mark a coroutine as cron-scheduled. Accepts standard 5-field crontab syntax.

    Implementation: turns the function into a task (queue ``cron``, retries 0)
    and records the (task, expression) pair on the module registry. Adapters
    pick it up in ``startup()`` and dispatch to whatever scheduler they prefer
    (Dramatiq's, Celery-beat, Arq's ``cron_jobs``, ``apscheduler`` for the
    in-process reference).
    """

    def decorator(fn: Callable[..., Awaitable[Any]]) -> TaskRef:
        ref = task(queue="cron", retries=0)(fn)
        _cron_jobs.append((ref, expr))
        return ref

    return decorator


def registered_tasks() -> dict[str, TaskRef]:
    """Snapshot of every ``@task`` registered. Adapters use this on startup."""
    return dict(_registered_tasks)


def cron_jobs() -> list[tuple[TaskRef, str]]:
    """Snapshot of every ``@cron`` registration."""
    return list(_cron_jobs)


def _clear() -> None:
    """For tests. Reset the module registries between cases."""
    _registered_tasks.clear()
    _cron_jobs.clear()


# ---------------------------------------------------------------------------
# Adapter selection: a contextvar holds the active adapter so a request can
# operate against a different adapter (e.g. ``tasks_eager()``) without global
# mutation.
# ---------------------------------------------------------------------------


_adapter_var: ContextVar[Any] = ContextVar("_quay_task_adapter")


def set_adapter(adapter: Any) -> None:
    """Install the default adapter the rest of the process will use."""
    _adapter_var.set(adapter)


def _active_adapter() -> Any:
    try:
        return _adapter_var.get()
    except LookupError as exc:
        msg = (
            "No TaskAdapter registered. Call quay.tasks.set_adapter(...) at boot, "
            "or use a TaskAdapter plugin in src/app/plugins.py."
        )
        raise RuntimeError(msg) from exc


def _encode(args: tuple[Any, ...], kwargs: dict[str, Any]) -> bytes:
    """JSON-encode positional + keyword args. Adapters override if they want
    msgspec or pickle; the contract is just ``bytes``.
    """
    return json.dumps({"args": list(args), "kwargs": kwargs}).encode()


def _decode(payload: bytes) -> tuple[tuple[Any, ...], dict[str, Any]]:
    data = json.loads(payload)
    return tuple(data.get("args", [])), data.get("kwargs", {})


# ---------------------------------------------------------------------------
# Reference adapter: in-process. Real adapters (Dramatiq, Celery) live in
# sibling packages.
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _RunRecord:
    state: TaskState
    fut: asyncio.Future[Any] = field(
        default_factory=lambda: asyncio.get_event_loop().create_future()
    )


class InMemoryAdapter:
    """In-process reference adapter.

    Each ``enqueue`` schedules an ``asyncio.Task`` that runs the underlying
    function with the decoded payload. Status / result are kept in a dict so
    a caller can poll. ``eager()`` switches to synchronous execution — useful
    in tests that want to assert on task side-effects before the test exits.

    Retry/backoff: the in-memory adapter implements ``fixed`` /``linear`` /
    ``exponential`` with a 100 ms base.
    """

    contract_version: ClassVar[str] = "v1.0"

    def __init__(self) -> None:
        self._records: dict[str, _RunRecord] = {}
        self._cron_tasks: list[asyncio.Task[None]] = []
        self._inflight: set[asyncio.Task[None]] = set()
        self._eager = False

    def _spawn(self, coro: Awaitable[None]) -> None:
        t = asyncio.create_task(coro)  # type: ignore[arg-type]
        self._inflight.add(t)
        t.add_done_callback(self._inflight.discard)

    async def startup(self, settings: Any) -> None:
        set_adapter(self)
        # Cron handling: scan the global registry and spin a per-job loop.
        for ref, expr in cron_jobs():
            self._cron_tasks.append(asyncio.create_task(self._cron_loop(ref, expr)))

    async def shutdown(self) -> None:
        for t in self._cron_tasks:
            t.cancel()
        for t in self._cron_tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await t
        self._cron_tasks.clear()
        self._records.clear()

    async def ready(self) -> bool:
        return True

    async def enqueue(self, task: TaskRef, payload: bytes) -> str:
        task_id = uuid.uuid4().hex
        record = _RunRecord(state=TaskState(state="pending"))
        self._records[task_id] = record

        coro = self._run(task, task_id, payload)
        if self._eager:
            await coro
        else:
            self._spawn(coro)
        return task_id

    async def schedule(self, task: TaskRef, when: datetime, payload: bytes) -> str:
        delay = max(0.0, (when - datetime.now(when.tzinfo)).total_seconds())
        task_id = uuid.uuid4().hex
        record = _RunRecord(state=TaskState(state="pending"))
        self._records[task_id] = record

        async def later() -> None:
            await asyncio.sleep(delay)
            await self._run(task, task_id, payload)

        self._spawn(later())
        return task_id

    async def cron(self, task: TaskRef, expr: str) -> None:
        # Cron registration is handled in ``startup()`` from the module registry;
        # external callers who hand-roll a TaskRef can register here.
        self._cron_tasks.append(asyncio.create_task(self._cron_loop(task, expr)))

    def eager(self) -> contextlib.AbstractAsyncContextManager[None]:
        return self._eager_context()

    @contextlib.asynccontextmanager
    async def _eager_context(self) -> AsyncIterator[None]:
        prev = self._eager
        self._eager = True
        try:
            yield
        finally:
            self._eager = prev

    async def status(self, task_id: str) -> TaskState:
        record = self._records.get(task_id)
        if record is None:
            return TaskState(state="failed", error=f"unknown task {task_id}")
        return record.state

    async def result(self, task_id: str) -> Any:
        record = self._records.get(task_id)
        if record is None:
            msg = f"unknown task {task_id}"
            raise KeyError(msg)
        return await record.fut

    # -- internals ----------------------------------------------------------

    async def _run(self, task: TaskRef, task_id: str, payload: bytes) -> None:
        record = self._records[task_id]
        if task.fn is None:
            record.state = TaskState(state="failed", error=f"{task!r} has no callable")
            record.fut.set_exception(RuntimeError(record.state.error))
            return
        args, kwargs = _decode(payload)
        record.state = TaskState(state="running")
        attempt = 0
        last_exc: BaseException | None = None
        while attempt <= task.retries:
            try:
                result = await task.fn(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                if attempt == task.retries:
                    break
                await asyncio.sleep(_backoff_delay(task.backoff, attempt))
                attempt += 1
                continue
            record.state = TaskState(state="complete", result=result)
            if not record.fut.done():
                record.fut.set_result(result)
            return
        record.state = TaskState(state="failed", error=str(last_exc))
        if not record.fut.done():
            assert last_exc is not None
            record.fut.set_exception(last_exc)

    async def _cron_loop(self, task: TaskRef, expr: str) -> None:
        """Minimal cron loop. The reference impl parses 5-field crontab and
        sleeps until the next match. Production adapters (Dramatiq / Celery)
        delegate to a real scheduler.
        """
        try:
            from quay._cron import next_fire

            while True:
                delay = next_fire(expr, datetime.now())
                await asyncio.sleep(delay)
                await self.enqueue(task, _encode((), {}))
        except asyncio.CancelledError:
            raise
        except Exception:
            _log.exception("cron loop crashed for %r", task)


def _backoff_delay(strategy: Backoff, attempt: int) -> float:
    base = 0.1
    if strategy == "fixed":
        return base
    if strategy == "linear":
        return base * (attempt + 1)
    return base * (2**attempt)


# ---------------------------------------------------------------------------
# Public testing entry point: ``tasks_eager()``. Pull the active adapter and
# enter its ``eager()`` context.
# ---------------------------------------------------------------------------


def tasks_eager() -> contextlib.AbstractAsyncContextManager[None]:
    return _active_adapter().eager()


__all__ = [
    "Backoff",
    "InMemoryAdapter",
    "TaskRef",
    "TaskState",
    "cron",
    "cron_jobs",
    "registered_tasks",
    "set_adapter",
    "task",
    "tasks_eager",
]
