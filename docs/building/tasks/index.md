# Background tasks

Causeway defines a `TaskAdapter` contract in core and ships `InMemoryAdapter` as the reference. Real adapters (Dramatiq, Celery, Arq, TaskIQ) live in sibling packages — pick one with a single line in `plugins.py`.

## Defining a task

```python
# src/app/tasks/emails.py
from causeway import task


@task(queue="emails", retries=5, backoff="exponential")
async def send_welcome(user_id: str) -> None:
    user = await load_user(user_id)
    await mailer.send(to=user.email, template="welcome")
```

`@task` returns a `TaskRef`. Calling the function directly raises — you have to go through `.enqueue(...)` so the failure mode is obvious.

## Enqueuing

```python
# src/app/routes/users/index.py
from app.tasks.emails import send_welcome
from causeway import post


@post
async def create(data: NewUser) -> User:
    user = await db.insert(...)
    await send_welcome.enqueue(user.id)
    return user
```

`.enqueue(...)` returns a task ID; the registered adapter handles persistence and delivery.

## Scheduling

```python
from datetime import datetime, timedelta, UTC

await send_welcome.schedule(
    datetime.now(UTC) + timedelta(minutes=15),
    user_id,
)
```

## Cron

```python
from causeway import cron

@cron("0 * * * *")            # every hour
async def hourly() -> None:
    await refresh_embeddings.enqueue()
```

Standard 5-field crontab syntax. The cron loop is owned by the adapter — Dramatiq has its own scheduler, Celery has `celery-beat`, Arq has `cron_jobs`, the in-memory adapter uses an internal loop.

## Adapter swap

```python
# src/app/plugins.py
from causeway import register
from causeway_tasks_dramatiq import DramatiqAdapter

register(DramatiqAdapter(broker_url="redis://localhost"))
```

Swap to Celery in one line:

```python
from causeway_tasks_celery import CeleryAdapter

register(CeleryAdapter(broker_url="redis://localhost"))
```

The `@task` and `.enqueue(...)` code doesn't move.

For in-process tests, the reference adapter is built in:

```python
from causeway.tasks import InMemoryAdapter

register(InMemoryAdapter())
```

## Retry and backoff

```python
@task(
    queue="webhooks",
    retries=3,
    backoff="exponential",   # "fixed" | "linear" | "exponential"
)
async def deliver_webhook(...): ...
```

- `fixed` — same delay between attempts.
- `linear` — `base * (attempt + 1)`.
- `exponential` — `base * 2^attempt`.

The in-memory adapter uses a 100ms base. Real adapters (Dramatiq, Celery) typically default to seconds — check the adapter's docs.

## Eager mode for tests

Every adapter implements `eager()` — inside the context, `.enqueue(...)` runs the task body in-process synchronously:

```python
from causeway.testing import tasks_eager

async def test_create_user(app):
    async with tasks_eager():
        r = await app.post("/users", json={"name": "ada"})
    assert r.status_code == 201
    # send_welcome already ran by now; assert on its side effects
```

This is part of the `TaskAdapter` contract — adapters that can't provide eager mode (rare) fail loudly at boot.

## Task results

```python
task_id = await send_welcome.enqueue(user_id)
state = await adapter.status(task_id)          # "pending" | "running" | "complete" | "failed"
result = await adapter.result(task_id)          # blocks until the task is done
```

The result surface is intentionally small. For workflows / DAGs, reach for Temporal / Prefect — Causeway isn't trying to be a workflow engine.

## Contract shape

```python
class TaskAdapter(Protocol):
    contract_version: ClassVar[str] = "v1.0"

    async def enqueue(self, task: TaskRef, payload: bytes) -> str: ...
    async def schedule(self, task: TaskRef, when: datetime, payload: bytes) -> str: ...
    async def cron(self, task: TaskRef, expr: str) -> None: ...
    def eager(self) -> AsyncContextManager[None]: ...
    async def status(self, task_id: str) -> TaskStatus: ...
    async def result(self, task_id: str) -> Any: ...
```

Small on purpose. Real adapters layer their own features (Dramatiq middleware, Celery workflows, Arq pipelines) under the same surface.

## What's _not_ in the contract

- **Distributed locks, leader election, semaphores** — `causeway-locks-*` plugins or user code.
- **Workflows / DAGs** — Temporal / Prefect / Apache Airflow.
- **Long-running task result streaming** — that's the `stream[T]` route primitive composed with a `@task`; see [Streaming](../handlers/streaming.md).

## Next

- [Reference — `@task`](../../api-reference/decorators/task.md)
- [Reference — `@cron`](../../api-reference/decorators/cron.md)
- [Reference — `TaskRef`](../../api-reference/classes/TaskRef.md)
- [Testing](../testing/index.md)
