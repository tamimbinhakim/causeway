# `@task`

Mark a coroutine as a background task.

```python
from causeway import task

@task(queue="emails", retries=5, backoff="exponential")
async def send_welcome(user_id: str) -> None:
    ...
```

## Signature

```python
task(
    *,
    queue: str = "default",
    retries: int = 0,
    backoff: Literal["fixed", "linear", "exponential"] = "exponential",
) -> Callable[[Coroutine], TaskRef]
```

Returns a [`TaskRef`](../classes/TaskRef.md) (not a function). Calling the ref directly raises — go through `.enqueue(...)` or `.schedule(...)`.

## Options

| Option    | Default        | Notes                                                                          |
| --------- | -------------- | ------------------------------------------------------------------------------ |
| `queue`   | `"default"`    | Adapter-specific queue / channel name.                                         |
| `retries` | `0`            | How many times to retry on exception.                                          |
| `backoff` | `"exponential"`| `"fixed"` (constant), `"linear"` (`base * (n+1)`), `"exponential"` (`base * 2^n`). |

The in-memory reference adapter uses a 100ms base. Real adapters typically use seconds — check the adapter's docs.

## Enqueuing

```python
task_id: str = await send_welcome.enqueue(user_id)
```

## Scheduling

```python
from datetime import datetime, timedelta, UTC

await send_welcome.schedule(datetime.now(UTC) + timedelta(minutes=15), user_id)
```

## Eager execution (tests)

```python
from causeway.testing import tasks_eager

async with tasks_eager():
    await send_welcome.enqueue(user_id)   # runs inline, synchronously
```

## See also

- [Tasks overview](../../building/tasks/index.md)
- [`@cron`](./cron.md)
- [`TaskRef`](../classes/TaskRef.md)
- [`tasks_eager`](../functions/tasks-eager.md)
