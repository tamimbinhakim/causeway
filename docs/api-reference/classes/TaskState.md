# `TaskState`

Snapshot returned by `TaskAdapter.status(task_id)`.

```python
from causeway.tasks import TaskState
```

## Shape

```python
@dataclass
class TaskState:
    state: Literal["pending", "running", "complete", "failed", "cancelled"]
    result: Any = None
    error: str | None = None
```

`"cancelled"` is terminal — set when `TaskAdapter.cancel(...)` succeeds, either because the task body cooperated (saw `cancel_requested()` and returned / raised) or because the adapter hard-cancelled it after the grace window. The task future, if awaited, raises `asyncio.CancelledError`.

## Usage

```python
task_id = await send_welcome.enqueue("user-1")
state = await adapter.status(task_id)

match state.state:
    case "complete":
        print(state.result)
    case "failed":
        print(state.error)
    case "cancelled":
        print("stopped on request")
    case _:
        print("not done yet")
```

## See also

- [`TaskRef`](./TaskRef.md)
- [`TaskAdapter`](./contracts.md#taskadapter) (in contracts)
- [`cancel_requested`](../functions/cancel-requested.md) / [`raise_if_cancelled`](../functions/raise-if-cancelled.md)
