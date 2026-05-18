# Events

Domain events sit a layer above background tasks. A route says "a customer was just created"; a listener decides what to do about it (send a welcome email, warm a cache, fire a webhook). Producers don't grow with consumers.

Discovery is file-based, like routes. Drop a file in `src/app/events/`, and every module-level `async def` in it becomes a listener for the event named by the file path. No decorator, no registration call, no string-name argument.

## Filename → event name

| File                                  | Event name              |
| ------------------------------------- | ----------------------- |
| `app/events/customer.create.py`       | `customer:create`       |
| `app/events/customer.delete.py`       | `customer:delete`       |
| `app/events/invoice.paid.py`          | `invoice:paid`          |
| `app/events/billing/refund.issued.py` | `billing:refund:issued` |
| `app/events/customer/create.py`       | `customer:create`       |

Rules:

- File stem split on `.`, joined with `:`.
- Folders are leading segments.
- Underscore-prefixed files and directories are skipped (colocated helpers).
- Two files producing the same event name **merge** their listeners — flat and nested forms can coexist.

Pick the flat form by default. Nest a folder only when one event grows enough listeners that a single file feels crowded.

## Writing a listener

```python
# src/app/events/customer.create.py
from app.models import Customer
from app.tasks.emails import send_welcome


async def email_welcome(customer: Customer) -> None:
    await send_welcome.enqueue(customer.id)


async def warm_cache(customer: Customer) -> None:
    await cache.set(f"customer:{customer.id}", customer)
```

Every module-level `async def` whose name doesn't start with `_` is a listener. The function name has no semantic role — it's there for readability and for stack traces. Sync defs, constants, and helpers are ignored.

## Emitting

```python
# src/app/routes/customers/index.py
from causeway import emit, post
from app.models import Customer


@post
async def create(data: NewCustomer) -> Customer:
    customer = await db.insert(...)
    await emit("customer:create", customer)
    return customer
```

`emit` runs every listener for the event concurrently (`asyncio.gather`). The first failure raises out of `emit`; remaining listeners' completion is not awaited. Emitting an event with no listeners is a no-op.

## Listeners enqueue tasks for durable work

The in-memory bus is best-effort. If a listener does work that has to survive a crash (sending an email, charging a card, calling a downstream API), enqueue a task from the listener — the task adapter handles persistence and retries.

```python
# src/app/events/order.placed.py
from app.tasks.fulfillment import charge_card, ship_order


async def charge(order):
    await charge_card.enqueue(order.id)


async def ship(order):
    await ship_order.enqueue(order.id)
```

Listeners that only do in-memory work (cache warms, metric increments, log lines) can stay inline.

## Boot

`create_app("app/routes", events_root="app/events")` discovers the events folder if it exists and installs an `InMemoryEventBus`. If `app/events/` is absent, no bus is installed — `await emit(...)` raises. That's intentional: the missing folder isn't a silent feature toggle.

## Testing

Listeners are plain async functions; import and call one directly:

```python
async def test_warm_cache_sets_key():
    from app.events.customer.create import warm_cache
    await warm_cache(Customer(id="abc"))
    assert await cache.get("customer:abc") is not None
```

End-to-end through `emit`:

```python
from causeway.events import InMemoryEventBus, discover, register, set_bus

async def test_create_route_fans_out(tmp_path):
    bus = InMemoryEventBus()
    await bus.startup(settings=None)
    set_bus(bus)
    register(discover("src/app/events"))
    # ... call the route, assert side effects
```

When a listener uses `task.enqueue`, combine with `tasks_eager()`:

```python
from causeway import tasks_eager

async def test_welcome_email_sent():
    async with tasks_eager():
        await emit("customer:create", customer)
    # send_welcome already ran
```

## Error policy

Listeners run via `asyncio.gather(*coros)` with the default `return_exceptions=False`. The first listener to raise propagates out of `emit`; the other listeners' coroutines are not awaited and may show up in unhandled-task warnings. If you need per-listener isolation, catch inside the listener:

```python
async def best_effort(payload):
    try:
        await flaky_call(payload)
    except Exception:
        log.exception("best_effort listener failed")
```

This is deliberately strict: a silently-swallowed listener failure is the kind of bug you don't notice until production. If you want fan-out-and-collect-errors semantics, build it on top of `emit` (or use a durable bus that ships in a plugin).

## What's _not_ in the contract

- **Durable delivery.** The in-memory bus doesn't persist. If you crash mid-emit, listeners that haven't started yet don't run. A transactional-outbox bus will arrive as a plugin (`causeway-events-*`); until then, push durability into the listeners that need it.
- **Listener ordering.** Listeners run concurrently. If you need ordering, do the sequence inside one listener.
- **Wildcards / subscriptions at runtime.** The event-name → listener map is built at boot from the filesystem and frozen. Dynamic subscribe/unsubscribe isn't supported — that's a different primitive (`PubSub` contract).
- **Cross-process fan-out.** In-process only. For cross-service events use webhooks or a real broker.

## Adapter swap

The bus is plugin-shaped — a `EventBus` Protocol lives in `causeway.contracts`. The default `InMemoryEventBus` is what `create_app` installs; durable adapters ship in sibling packages and swap in via `register(...)` in `plugins.py`, exactly like the `TaskAdapter` swap.

```python
# src/app/plugins.py
from causeway import register
from causeway_events_redis import RedisEventBus

register(RedisEventBus(url="redis://localhost"))
```

The listener files don't move.

## Next

- [Reference — `emit`](../../api-reference/functions/emit.md)
- [Reference — `EventBus` contract](../../api-reference/classes/contracts.md)
- [Background tasks](../tasks/index.md) — what listeners typically enqueue
- [Webhooks (outgoing)](../webhooks/index.md) — when the consumer lives in another service
