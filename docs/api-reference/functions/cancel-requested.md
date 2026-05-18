# `cancel_requested`

Return `True` if the current task has been asked to cancel.

```python
from causeway.tasks import cancel_requested
```

## Signature

```python
def cancel_requested() -> bool
```

Inside a `@task` body, returns `True` once `TaskAdapter.cancel(task_id, ...)` has been called for this run. Outside a task — or for adapters that don't support cancellation — it always returns `False`, so the helper is safe to sprinkle in shared utility code.

## Usage

Poll between units of work and exit cleanly when the flag flips:

```python
from causeway import task
from causeway.tasks import cancel_requested


@task()
async def reindex_everything() -> None:
    async for doc in stream_docs():
        if cancel_requested():
            return                    # state transitions to "cancelled"
        await search.index(doc)
```

A clean `return` after seeing the flag is recorded as `state="cancelled"` — not `"complete"` — so callers can distinguish "you stopped because I asked" from "you finished the work."

## When to prefer `raise_if_cancelled` instead

If you'd rather raise at checkpoints than branch on a boolean, use [`raise_if_cancelled`](./raise-if-cancelled.md):

```python
await raise_if_cancelled()
```

It raises `asyncio.CancelledError`, which the adapter recognizes as a cancel.

## See also

- [`raise_if_cancelled`](./raise-if-cancelled.md)
- [Tasks — Cancellation](../../building/tasks/index.md#cancellation)
- [`TaskAdapter.cancel`](../classes/contracts.md#taskadapter)
- [`TaskState`](../classes/TaskState.md)
