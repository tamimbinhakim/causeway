# `TaskRef`

Handle returned by [`@task`](../decorators/task.md). Identifies a registered task and exposes the methods to dispatch it.

```python
from causeway import task

@task(queue="emails", retries=3)
async def send_welcome(user_id: str) -> None: ...

# send_welcome is now a TaskRef, not a function.
await send_welcome.enqueue("user-1")
```

## Shape

```python
@dataclass
class TaskRef:
    module: str             # e.g. "app.tasks.emails"
    name: str               # e.g. "send_welcome"
    queue: str = "default"
    retries: int = 0
    backoff: Literal["fixed", "linear", "exponential"] = "exponential"
    fn: Callable | None     # the original async function
```

## Methods

```python
await task_ref.enqueue(*args, **kwargs) -> str
await task_ref.schedule(when: datetime, *args, **kwargs) -> str
```

- Returns a task ID (adapter-defined string).
- Args/kwargs are JSON-serialized as the payload.
- Calling `task_ref(...)` directly raises — go through `.enqueue(...)` or `.schedule(...)`.

## Why a Ref instead of the function

So the failure mode is obvious. If `@task` returned the original function, you could call it in-band by forgetting `.enqueue` — and the side effects would run synchronously in the request path. The `TaskRef` wall forces the dispatch through the adapter.

## Adapter integration

Adapters identify a task by `module + name` so a queued job survives a process restart. The `fn` attribute is kept on the ref so the in-process / eager adapter can dispatch without an import lookup.

## See also

- [Tasks](../../app/tasks.md)
- [`@task`](../decorators/task.md)
- [`TaskState`](./TaskState.md)
