# `Event.emit()`

Dispatch a typed event to its in-process listeners and (when `webhook = True`) outbound subscribers.

```python
from app.events.customer_created import CustomerCreated

await CustomerCreated(id=user.id, email=user.email).emit()
```

> **Note.** The 0.1 `emit(name: str, payload: Any)` function has been removed. Events are now class-based — see [Events](../../building/events/index.md) for the new model.

## Signature

```python
async def emit(self) -> EmitResult: ...
```

`emit` is an instance method on `Event` subclasses. It takes no arguments (the payload is `self`).

## Behavior

1. **In-process fan-out.** Runs every `@<Cls>.listen` listener registered against the class. Listeners run concurrently via `asyncio.gather`. The first listener to raise propagates out of `emit`; the remaining listeners' coroutines are not awaited.
2. **Webhook fan-out** (only when `<Cls>.webhook = True`). Walks `_subscribers` (static, file-discovered) plus the active `WebhookStore`'s rows (dynamic, if installed). For each subscriber whose `where` filter matches the event instance, enqueues one `_deliver` task. Tasks are not awaited; the caller never blocks on outbound HTTP.

Returns an `EmitResult`:

```python
@dataclass
class EmitResult:
    delivery_ids: list[str]  # task ids of enqueued webhook deliveries
```

Empty list when the class has `webhook = False` or no subscribers matched.

## Failure modes

| Source                      | Surface                                                          |
| --------------------------- | ---------------------------------------------------------------- |
| Listener raises             | First exception propagates out of `emit`                         |
| Webhook enqueue fails       | Logged, that subscriber's delivery skipped, others continue      |
| Webhook delivery POST fails | Handled by the task adapter's retry chain; not visible to `emit` |

## See also

- [Events overview](../../building/events/index.md)
- [Webhooks](../../building/webhooks/index.md)
- [Subscribers](../../building/subscribers/index.md)
- [Testing — `captured()` / `captured_webhooks()`](../../building/testing/index.md)
