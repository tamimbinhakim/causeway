# `raise_if_cancelled`

Raise `asyncio.CancelledError` if the current task has been asked to cancel.

```python
from causeway.tasks import raise_if_cancelled
```

## Signature

```python
async def raise_if_cancelled() -> None
```

The "checkpoint" form of [`cancel_requested`](./cancel-requested.md). If `TaskAdapter.cancel(task_id, ...)` has been called for this run, it raises `asyncio.CancelledError`; otherwise it's a cheap no-op. Outside a task, or for adapters that don't support cancellation, it never raises.

## Usage

Sprinkle at natural checkpoints in a loop:

```python
from causeway import task
from causeway.tasks import raise_if_cancelled


@task()
async def reindex_everything() -> None:
    async for doc in stream_docs():
        await raise_if_cancelled()
        await search.index(doc)
```

The adapter recognizes `CancelledError` from a task body and records `state="cancelled"`. Awaiting `adapter.result(task_id)` afterwards re-raises `CancelledError` to the caller.

## When to prefer `cancel_requested` instead

When you need to run cleanup code before returning, use the boolean form so the cleanup path is explicit:

```python
if cancel_requested():
    await release_resources()
    return
```

## See also

- [`cancel_requested`](./cancel-requested.md)
- [Tasks — Cancellation](../../building/tasks/index.md#cancellation)
- [`TaskAdapter.cancel`](../classes/contracts.md#taskadapter)
- [`TaskState`](../classes/TaskState.md)
