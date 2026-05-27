"""Long-running jobs via a pluggable queue.

Submit a coroutine returning ``T``, get a task-id back, poll
``backend.status(id)`` or iterate ``backend.stream(id)`` for live progress.
The backend is swappable — ``InMemoryBackend`` ships in core; Redis / SQS
adapters belong in their own packages so the core stays dependency-light.

Backend implementations expose four primitives: ``enqueue``, ``status``,
``stream``, ``cancel``. Anything that satisfies the ``TaskBackend``
Protocol qualifies.

``mount_task_routes`` wires one handler into the submit/status/stream
triple at a single path prefix, so a handler ``def transcribe(audio)``
mounted at ``/transcribe`` becomes ``POST /transcribe`` (submit),
``GET /transcribe/{task_id}`` (status), ``GET /transcribe/{task_id}/events``
(SSE progress).
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, Generic, Literal, Protocol, TypeVar, runtime_checkable

import msgspec

from causeway._runtime.streaming import stream

if TYPE_CHECKING:
    from causeway._runtime.app import App

T = TypeVar("T")

TaskStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]


@dataclass(slots=True)
class TaskState(Generic[T]):
    task_id: str
    status: TaskStatus
    result: T | None = None
    error: str | None = None
    progress: float = 0.0  # 0..1
    enqueued_at: float = 0.0
    started_at: float | None = None
    finished_at: float | None = None


@runtime_checkable
class TaskBackend(Protocol):
    """Minimal queue interface. Adapter packages (Redis/SQS) implement this."""

    async def enqueue(
        self, fn: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any
    ) -> str: ...

    async def status(self, task_id: str) -> TaskState[Any]: ...

    def stream(self, task_id: str) -> AsyncIterator[TaskState[Any]]: ...

    async def cancel(self, task_id: str) -> None: ...


@dataclass(slots=True)
class _InMemoryRecord:
    state: TaskState[Any]
    task: asyncio.Task[Any] | None = None
    listeners: list[asyncio.Queue[TaskState[Any]]] = field(
        default_factory=lambda: [],
    )


class InMemoryBackend:
    """Single-process backend. Loses everything on restart — for dev and tests.

    Production deployments swap this for the Redis / SQS adapter packages.
    """

    def __init__(self) -> None:
        self._records: dict[str, _InMemoryRecord] = {}

    async def enqueue(self, fn: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> str:
        task_id = uuid.uuid4().hex
        record = _InMemoryRecord(
            state=TaskState(task_id=task_id, status="queued", enqueued_at=time.time()),
        )
        self._records[task_id] = record

        async def runner() -> None:
            self._broadcast(record, "running", started_at=time.time())
            try:
                result = await fn(*args, **kwargs)
            except asyncio.CancelledError:
                self._broadcast(record, "cancelled", finished_at=time.time())
                raise
            except Exception as exc:
                self._broadcast(record, "failed", finished_at=time.time(), error=repr(exc))
                return
            self._broadcast(
                record, "succeeded", finished_at=time.time(), result=result, progress=1.0
            )

        record.task = asyncio.create_task(runner())
        return task_id

    def _broadcast(self, record: _InMemoryRecord, status: TaskStatus, **fields: Any) -> None:
        for k, v in fields.items():
            setattr(record.state, k, v)
        record.state.status = status
        snapshot = replace(record.state)
        for q in record.listeners:
            with contextlib.suppress(asyncio.QueueFull):  # pragma: no cover
                q.put_nowait(snapshot)

    async def status(self, task_id: str) -> TaskState[Any]:
        record = self._records.get(task_id)
        if record is None:
            raise KeyError(task_id)
        return replace(record.state)

    async def stream(self, task_id: str) -> AsyncIterator[TaskState[Any]]:
        record = self._records.get(task_id)
        if record is None:
            raise KeyError(task_id)
        queue: asyncio.Queue[TaskState[Any]] = asyncio.Queue(maxsize=64)
        record.listeners.append(queue)
        # Replay current state once so consumers don't miss the initial value.
        queue.put_nowait(replace(record.state))
        try:
            while True:
                state = await queue.get()
                yield state
                if state.status in ("succeeded", "failed", "cancelled"):
                    return
        finally:
            with contextlib.suppress(ValueError):  # pragma: no cover
                record.listeners.remove(queue)

    async def cancel(self, task_id: str) -> None:
        record = self._records.get(task_id)
        if record is None or record.task is None:
            return
        record.task.cancel()


class TaskSubmission(msgspec.Struct):
    """Response shape from the submit route — clients poll ``task_id`` for progress."""

    task_id: str


def mount_task_routes(
    app: App,
    path: str,
    handler: Callable[..., Awaitable[Any]],
    *,
    backend: TaskBackend,
) -> None:
    """Register submit / status / stream routes for a long-running handler.

    Three routes get added at ``path``:

    - ``POST <path>``: validates handler inputs, calls ``backend.enqueue``,
      returns ``{"task_id": "..."}``. Inputs are taken from the handler's
      own signature, so query/body/path conventions are identical to a
      regular causeway route.
    - ``GET <path>/{task_id}``: returns ``TaskState[T]`` (a one-shot poll).
    - ``GET <path>/{task_id}/events``: SSE stream of ``TaskState[T]``
      updates, terminating once the task reaches a final status.

    The handler's return type ``T`` is reused as the ``TaskState[T]``
    payload — both status and stream routes round-trip a result of the
    same shape.
    """
    import typing as _typing

    handler_sig = inspect.signature(handler)
    handler_localns: dict[str, Any] | None = getattr(handler, "__causeway_localns__", None)
    # Forward the *handler's* module globals (plus any captured localns) so
    # ``typing.get_type_hints`` can resolve string annotations on the wrappers,
    # whose own ``__globals__`` would be this module (tasks.py).
    handler_globals: dict[str, Any] = getattr(handler, "__globals__", {})
    forward_ns: dict[str, Any] = {**handler_globals}
    if handler_localns:
        forward_ns.update(handler_localns)

    handler_hints = _typing.get_type_hints(handler, localns=forward_ns, include_extras=True)
    result_type: Any = handler_hints.get("return", Any)
    state_type = TaskState[result_type] if result_type is not Any else TaskState[Any]

    async def submit(**kwargs: Any) -> TaskSubmission:
        task_id = await backend.enqueue(handler, **kwargs)
        return TaskSubmission(task_id=task_id)

    submit.__name__ = f"submit_{handler.__name__}"
    submit.__qualname__ = submit.__name__
    setattr(submit, "__signature__", handler_sig.replace(return_annotation=TaskSubmission))  # noqa: B010
    submit.__annotations__ = {**handler.__annotations__, "return": TaskSubmission}

    async def status(task_id: str) -> TaskState[Any]:
        try:
            return await backend.status(task_id)
        except KeyError:
            from causeway._runtime.runtime import ValidationError

            raise ValidationError(
                "task not found",
                location="path",
                field="task_id",
                value=task_id,
            ) from None

    status.__name__ = f"status_{handler.__name__}"
    status.__qualname__ = status.__name__
    status.__annotations__ = {"task_id": str, "return": state_type}

    async def events(task_id: str) -> AsyncIterator[TaskState[Any]]:
        try:
            iterator = backend.stream(task_id)
        except KeyError:
            from causeway._runtime.runtime import ValidationError

            raise ValidationError(
                "task not found",
                location="path",
                field="task_id",
                value=task_id,
            ) from None
        async for state in iterator:
            yield state

    events.__name__ = f"events_{handler.__name__}"
    events.__qualname__ = events.__name__
    # ``state_type`` is a runtime value (parameterised generic); mypy can't
    # treat it as a type form, so we stash it dict-side. The runtime reads
    # ``__annotations__`` reflectively — it cares about the value, not the
    # static type-system view.
    events.__annotations__ = {"task_id": str, "return": stream[state_type]}  # type: ignore[valid-type]

    app.post(path)(submit)
    app.get(f"{path}/{{task_id}}")(status)
    app.get(f"{path}/{{task_id}}/events")(events)
    # ``app._register`` stamps each handler's ``__causeway_localns__`` with its
    # *caller's* frame locals — which here is this function, not the user's
    # module. Overwrite with the handler's resolved namespace so deferred
    # annotations like ``-> TranscribeInput`` resolve correctly later.
    setattr(submit, "__causeway_localns__", forward_ns)  # noqa: B010
