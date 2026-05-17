# `TaskState`

Snapshot returned by `TaskAdapter.status(task_id)`.

```python
from causeway.tasks import TaskState
```

## Shape

```python
@dataclass
class TaskState:
    state: Literal["pending", "running", "complete", "failed"]
    result: Any = None
    error: str | None = None
```

## Usage

```python
task_id = await send_welcome.enqueue("user-1")
state = await adapter.status(task_id)

match state.state:
    case "complete":
        print(state.result)
    case "failed":
        print(state.error)
    case _:
        print("not done yet")
```

## See also

- [`TaskRef`](./TaskRef.md)
- [`TaskAdapter`](./contracts.md#taskadapter) (in contracts)
