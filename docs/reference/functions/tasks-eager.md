# `tasks_eager`

Run enqueued tasks inline for the duration of an `async with` block.

```python
from causeway.testing import tasks_eager

async with tasks_eager():
    r = await app.post("/users", json={"name": "ada"})
# every .enqueue(...) inside the block ran synchronously
```

## Signature

```python
tasks_eager() -> AsyncContextManager[None]
```

Delegates to the active `TaskAdapter`'s `eager()` method. Every `TaskAdapter` is required to implement `eager()` — it's part of the contract.

## Behavior

Inside the block:

- `.enqueue(...)` runs the task body in-process, then returns the task id.
- `.schedule(...)` likewise — the `when` is ignored, the body runs immediately.
- Exceptions from the task body propagate to the caller of `.enqueue(...)`.

Outside the block, the adapter is back to its normal asynchronous behavior.

## Where to use it

Tests that want to assert on a task's side effects synchronously:

```python
async def test_signup_sends_welcome(app):
    async with tasks_eager():
        r = await app.post("/users", json={"name": "ada"})
    assert r.status_code == 201
    assert mailer.sent_to == ["ada@example.com"]   # send_welcome already ran
```

Don't use it in production code paths.

## See also

- [Testing](../../app/testing.md)
- [`@task`](../decorators/task.md)
- [Tasks overview](../../app/tasks.md)
