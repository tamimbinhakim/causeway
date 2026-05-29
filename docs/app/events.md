# Events

Domain events sit a layer above background tasks. A route says "a customer was just created"; a **listener** decides what to do in-process (send a welcome email, warm a cache); a **subscriber** decides what to deliver out-of-process (notify Slack, fire a partner's webhook). Producers don't grow with consumers, and the two channels share one definition.

Causeway's event model has three rules:

1. **One file per event.** Class declaration in `app/events/<name>.py`.
2. **Class name is canonical.** The class drives the wire name; the file just stores it.
3. **The class is the bus.** Listeners and subscribers register against the class itself — no separate bus to plug in.

## Defining an event

```python
# app/events/customer_created.py
from causeway.events import Event
from uuid import UUID

class CustomerCreated(Event):
    id: UUID
    email: str
```

That's everything. The class registers itself at import:

- `CustomerCreated.wire_name == "customer.created"` (PascalCase split on case boundaries → dot-separated lowercase)
- `CustomerCreated._listeners` starts empty
- `CustomerCreated._subscribers` starts empty
- `CustomerCreated.webhook == False`

Subclassing `Event` opts the class into `msgspec.Struct` semantics — fields are validated at construction, instances compare by value, JSON encoding is free.

### Filename ↔ class name

The convention is **snake_case of the PascalCase class name**:

| File                         | Class                   | Wire name                 |
| ---------------------------- | ----------------------- | ------------------------- |
| `customer_created.py`        | `CustomerCreated`       | `customer.created`        |
| `order_shipped.py`           | `OrderShipped`          | `order.shipped`           |
| `billing_invoice_created.py` | `BillingInvoiceCreated` | `billing.invoice.created` |
| `webhook_delivery_failed.py` | `WebhookDeliveryFailed` | `webhook.delivery.failed` |

Discovery validates this at boot: a `customer_created.py` containing `OrderShipped` is a hard error pointing at both. Two classes in one file is also a hard error — one event per file, no exceptions.

**No folders inside `events/`.** Use longer class names for sub-namespacing — `BillingInvoiceCreated` instead of `billing/invoice/created.py`. Dots in the wire name carry the namespace; folders would add nothing.

## Emitting

```python
# Construct then emit
await CustomerCreated(id=user.id, email=user.email).emit()

# Re-emit a typed instance you received from somewhere else
await received_event.emit()
```

Typos can't silently no-op — `CustmerCreated.emit` is an `ImportError` at the top of the file, not a runtime drop.

`.emit()` returns an `EmitResult` listing the webhook delivery task ids that were enqueued (empty list when `webhook = False` or no subscribers matched).

## Listening (in-process)

Listeners live in `app/listeners/`, named by **concern** (what they do), not by event:

```python
# app/listeners/welcome_email.py
from app.events.customer_created import CustomerCreated
from app.config import settings

@CustomerCreated.listen
async def send_welcome(p: CustomerCreated) -> None:
    await mailer.send(p.email, "Welcome", "...")
```

```python
# app/listeners/search_index.py
from app.events.customer_created import CustomerCreated
from app.events.customer_updated import CustomerUpdated

@CustomerCreated.listen
async def index_new(p: CustomerCreated) -> None:
    await search.index(p)

@CustomerUpdated.listen
async def reindex(p: CustomerUpdated) -> None:
    await search.update(p)
```

The same listener may react to multiple events; multiple listeners may react to the same event. Listeners run **concurrently** when an event is emitted — the first failure raises out of `.emit()`.

`@<Event>.listen` validates the signature at decoration time:

- Must be `async def`.
- Must take exactly one positional parameter.
- The parameter's annotation isn't enforced (Python forward-ref resolution at decoration time is unreliable) — your static checker is the right tool to catch type mismatches.

Plain `async def` files (no `@listen` decorator) are **not** auto-registered. Explicit registration is the only path.

## Webhook fan-out

To make an event also deliver to outbound subscribers, set `webhook = True` on the class:

```python
class CustomerCreated(Event):
    webhook = True
    id: UUID
    email: str
```

Now `.emit()` does two things atomically:

1. Awaits every in-process listener (raises on first failure).
2. Enqueues one delivery task per matching subscriber.

Listeners are awaited; deliveries are not. The caller never blocks on outbound HTTP. See [Webhooks](./webhooks.md) for the full subscriber model.

## File layout

```
app/
  events/                                 # one class per file
    customer_created.py                   # class CustomerCreated
    customer_updated.py                   # class CustomerUpdated
    order_shipped.py                      # class OrderShipped
  listeners/                              # named by concern
    welcome_email.py                      # @CustomerCreated.listen
    search_index.py                       # @CustomerCreated.listen, @CustomerUpdated.listen
    audit_log.py
  subscribers/                            # outbound webhook targets (optional)
    slack.py
```

Discovery walks all three at boot. Missing folders are skipped silently.

## Testing

Two context managers in `causeway.testing` short-circuit each delivery channel:

```python
from causeway.testing import captured, captured_webhooks

async def test_creating_customer_emits_event(client):
    async with captured(CustomerCreated) as events:
        await client.post("/customers", json={"email": "a@b"})
    assert len(events) == 1
    assert events[0].email == "a@b"

async def test_creating_customer_notifies_slack(client):
    async with captured_webhooks() as deliveries:
        await client.post("/customers", json={"email": "a@b"})
    assert len(deliveries) == 1
    assert deliveries[0].url == "https://slack.example"
```

`captured()` suppresses in-process listeners and records every emit of the given classes. `captured_webhooks()` suppresses outbound delivery and records what _would_ have been enqueued (one record per matching subscriber, `where` filter applied).

## Framework events

Causeway ships its own `Event` subclasses for runtime conditions you may want to react to. Subscribe to them from `app/listeners/`:

```python
# app/listeners/webhook_health.py
from causeway.webhooks import WebhookDeliveryFailed

_DISABLE_THRESHOLD = 10

@WebhookDeliveryFailed.listen
async def maybe_disable(p: WebhookDeliveryFailed) -> None:
    if p.attempts >= _DISABLE_THRESHOLD:
        # Mark the endpoint as disabled in your store...
        ...
```

Framework events have `webhook = False` so the failure-event isn't itself webhook-bridged (otherwise a broken endpoint would cascade into more failure deliveries).

## Why this shape

- **One symbol per event.** Rename `CustomerCreated` → IDE renames everywhere. Move the file → wire name updates automatically.
- **No magic strings.** `customer.created` lives in one place: the class name. You can't typo it; you can't get out of sync.
- **Listeners by concern, not by trigger.** `welcome_email.py` reads top-to-bottom as the welcome-email side effect across every event it cares about. Co-locating listeners inside the event file falls apart past 1:1 mappings.
- **Class IS the bus.** No separate `EventBus` to plug in, no `set_bus`, no install step. The plugin point moves down to durability (task adapter, webhook store).

## Migrating from the 0.1 event API

The 0.1 API was string-keyed (`await emit("customer:created", payload)`). It's been removed; there is no compatibility shim.

| 0.1                                              | 0.2+                                                                                             |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| `emit("x:y", payload)`                           | `await XY(...).emit()`                                                                           |
| `app/events/x.y.py` with `async def listener(p)` | `app/events/x_y.py` with `class XY(Event)`, listener moves to `app/listeners/` with `@XY.listen` |
| `InMemoryEventBus`, `set_bus`                    | gone — class IS the bus                                                                          |
| `EventBus` Protocol                              | gone — no event-bus plugin point                                                                 |
