# `emit`

Dispatch a domain event to every listener registered for it.

```python
from causeway import emit

await emit("customer:create", customer)
```

## Signature

```python
async def emit(name: str, payload: Any = None) -> None
```

Delegates to the active `EventBus`. `create_app` installs an `InMemoryEventBus` when `app/events/` exists.

## Parameters

| Parameter | Default | Notes                                                               |
| --------- | ------- | ------------------------------------------------------------------- |
| `name`    | —       | Event name, e.g. `"customer:create"`. Matches the filename mapping. |
| `payload` | `None`  | Single positional value passed to every listener as-is.             |

## Behavior

- Listeners run concurrently via `asyncio.gather(*coros)`.
- The first listener to raise propagates out of `emit`. Other listeners' coroutines are not awaited.
- Emitting an event with no listeners is a no-op (logs once at DEBUG).
- Calling `emit` without an active bus raises `RuntimeError`.

## Filename → event name

| File                                  | Event name                 |
| ------------------------------------- | -------------------------- |
| `app/events/customer.create.py`       | `customer:create`          |
| `app/events/billing/refund.issued.py` | `billing:refund:issued`    |
| `app/events/customer/create.py`       | `customer:create` (merged) |

See [Events](../../building/events/index.md) for the full convention.

## See also

- [Events overview](../../building/events/index.md)
- [`EventBus` contract](../classes/contracts.md)
- [Background tasks](../../building/tasks/index.md) — what listeners typically enqueue
