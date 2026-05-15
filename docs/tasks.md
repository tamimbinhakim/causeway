# Background tasks

Quay defines a **`TaskAdapter` contract** in core and ships **Dramatiq as the reference adapter**. Pick a real implementation (Celery, Arq, TaskIQ, in-process) by changing one line in `plugins.py`.

## Why a contract, not a queue

Per 2025 benchmarks: Huey, Dramatiq, and TaskIQ are roughly 10× faster than RQ for high-throughput no-op workloads; Celery remains the workflow-rich incumbent; Dramatiq strikes the best simplicity / reliability balance.

Quay doesn't pick. The framework defines what background jobs **are** (a callable with a payload schema, a queue, retry / backoff policy, and a status surface) and lets you plug in the broker.

## The decorator

```python
# src/app/tasks/emails.py
from quay import task

@task(queue="emails", retries=5, backoff="exponential")
async def send_welcome(user_id: str) -> None:
    user = await load_user(user_id)
    await mailer.send(to=user.email, template="welcome")
```

Calling from a handler:

```python
# src/app/routes/users/index.py
from app.tasks.emails import send_welcome
from quay import post

@post
async def create(data: NewUser) -> User:
    user = await db.insert(...)
    await send_welcome.enqueue(user.id)
    return user
```

`enqueue(...)` is adapter-agnostic. The handler stays the same when you swap brokers.

## Adapter swap

```python
# src/app/plugins.py
from quay import register
from quay_tasks_dramatiq import DramatiqAdapter  # reference

register(DramatiqAdapter(broker_url="redis://localhost"))
```

Want Celery? Change one line:

```python
from quay_tasks_celery import CeleryAdapter

register(CeleryAdapter(broker_url="redis://localhost"))
```

Want in-process for tests? Already built in:

```python
from quay.tasks import InMemoryAdapter

register(InMemoryAdapter())
```

## Cron

```python
from quay import cron
from app.tasks.ingest import refresh_embeddings

@cron("0 * * * *")            # every hour
async def hourly() -> None:
    await refresh_embeddings.enqueue()
```

Cron delegates to whatever `TaskAdapter` is registered. Dramatiq has its own scheduler; Celery has `celery-beat`; Arq has `cron_jobs`; the in-process adapter uses `apscheduler`.

## Eager mode (testing)

Every adapter must support `tasks_eager()`:

```python
from quay.testing import tasks_eager

async def test_create_user(app):
    async with tasks_eager():
        r = await app.post("/users", json={"name": "ada"})
    assert r.status_code == 201
```

Tasks run inline in the same process; `.enqueue(...)` returns only after the task body finishes, so the test can assert on its side-effects synchronously.

## Contract shape

```python
class TaskAdapter(Protocol):
    async def enqueue(self, task: TaskRef, payload: bytes) -> str: ...
    async def schedule(self, task: TaskRef, when: datetime, payload: bytes) -> str: ...
    async def cron(self, task: TaskRef, expr: str) -> None: ...
    def eager(self) -> AsyncContextManager[None]: ...

    # status surface — adapter decides storage
    async def status(self, task_id: str) -> TaskStatus: ...
    async def result(self, task_id: str) -> Any: ...
```

This is small on purpose. Real adapters layer their own features (Dramatiq middleware, Celery workflows, Arq pipelines) under the same surface.

## What's _not_ in the contract

- **Long-running task result streaming** is a separate `Task[T]` route-level primitive, not the queue. The two compose: a `@task` enqueues; a `Task[T]` route polls / streams the result back.
- **Distributed locks, leader election, semaphores**. Those belong in `quay-locks-*` plugins or in user code.
- **Workflows / DAGs**. Pick Temporal / Prefect / your-DAG-lib-of-choice. We're not reinventing.
