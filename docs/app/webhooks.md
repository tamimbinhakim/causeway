# Webhooks (outgoing)

An outbound webhook is a signed HTTP POST you send when one of your events fires. Causeway's webhook model has two kinds of recipients:

- **Static `Subscriber`** — declared in `app/subscribers/<name>.py`. URL/secret come from config. Used for fixed integrations (your Slack, your Datadog, a partner you always notify).
- **Dynamic subscription** — created at runtime through a `WebhookStore` plugin. Used when end users supply their own webhook URLs (multi-tenant, customer-managed integrations).

Both flavors plug into the same fan-out: `Event.emit()` walks every matching subscriber and enqueues one delivery task each. Delivery rides the [task adapter](./tasks.md) — the retry schedule, durability, and worker model are all the task system's, not bespoke webhook code.

## The signing format

Stripe-style HMAC-SHA256 over `f"{timestamp}.{body}"`:

```
X-Causeway-Signature: v1,<hex(hmac_sha256(secret, f"{ts}.{body}"))>
X-Causeway-Timestamp: <unix-seconds>
X-Causeway-Event: <wire-name>
```

The format is intentionally a copy of what Stripe popularized — well-understood, easy to verify, no novel cryptography.

## Defining an event for webhook delivery

Set `webhook = True` on the event class. That's it:

```python
# app/events/customer_created.py
from causeway.events import Event
from uuid import UUID

class CustomerCreated(Event):
    webhook = True
    organization_id: UUID
    id: UUID
    email: str
```

Emitting fan-outs to both channels in one call:

```python
await CustomerCreated(
    organization_id=org.id,
    id=user.id,
    email=user.email,
).emit()
# In-process listeners run concurrently (awaited).
# Webhook deliveries are scheduled as tasks (not awaited).
```

## Static subscribers

A `Subscriber` is a module-level instance in `app/subscribers/`. The file name is the subscriber id.

```python
# app/subscribers/slack.py
from causeway.webhooks import Subscriber
from app.events.customer_created import CustomerCreated
from app.events.payment_failed import PaymentFailed
from app.config import settings

slack = Subscriber(
    url=settings.slack_webhook_url,
    secret=settings.slack_signing_secret,
    events=[CustomerCreated, PaymentFailed],
)
```

On construction it registers itself against each event class's `_subscribers` list. Removing a subscriber means deleting the file — no runtime `disable_endpoint` call.

### Filtering with `where`

Subscribers can carry a `where` dict that exact-matches event fields. Only events whose field values match every key in `where` are delivered to that subscriber:

```python
# Static subscriber — only our staging org, only US-East region:
internal_monitor = Subscriber(
    url=settings.internal_monitor_url,
    secret=settings.internal_monitor_secret,
    events=[CustomerCreated],
    where={"organization_id": STAGING_ORG, "region": "us-east"},
)
```

Semantics:

- `where=None` (or omitted) → match every event of the subscribed types.
- Multiple keys AND together.
- Filter values must be JSON-serializable (the same shape is stored in dynamic subscriptions).
- Unknown keys (field doesn't exist on the event) → `ValueError` at module import, catching typos early.
- Equality is JSON-roundtrip permissive: `UUID("...")` and its string form compare equal.

## Dynamic subscriptions

For multi-tenant cases (customers paste their URL in a settings page), install a `WebhookStore` plugin and subscribe through it:

```python
# app/routes/settings/webhooks.py
@post
async def create_subscription(req: Request, *, store: WebhookStore) -> Response:
    secret = new_secret()                              # show ONCE; never logged
    endpoint_id = await store.subscribe(
        url=req.json["url"],
        secret=secret,
        events=[CustomerCreated.wire_name, OrderShipped.wire_name],  # strings
        where={"organization_id": current_user(req).org_id},          # scope to tenant
    )
    return Response.json({"id": endpoint_id, "secret": secret})
```

Dynamic subscribers reference events by **wire name string** because the public API can't pass `Event` classes (external callers don't import your Python). Static subscribers pass the class.

`InMemoryWebhookStore` is the reference implementation — process-local, not durable. Production deployments install a durable plugin (`causeway-webhooks-pg`, etc.). The in-memory store is fine for tests and single-process demos.

## Delivery

Delivery is a regular `@task` inside `causeway.webhooks`:

```python
@task(queue="webhooks", retries=5, backoff="exponential")
async def _deliver(*, url, secret, wire_name, body): ...
```

What you get from riding the task adapter:

- **Durability** — install `causeway-tasks-pg` and deliveries survive crashes. No `causeway-webhooks-pg` needed for delivery durability (only for subscription durability).
- **Multi-process workers** — already how tasks scale horizontally.
- **Backpressure** — queue depth is a task-adapter metric.
- **Cancellation** — already in `TaskAdapter` v1.1.
- **Observability** — `/admin/tasks` shows pending/failed deliveries per `queue="webhooks"`.

The body is signed inside the task (not at enqueue) so each retry uses a fresh timestamp. Long retry chains don't get rejected for stale signatures.

## Incoming webhooks

For receiving someone else's webhooks (Stripe, GitHub, partner integrations), use `verify`:

```python
# app/routes/(public)/webhooks/stripe.py
from causeway import post
from causeway.webhooks import verify
from app.events.subscription_started import SubscriptionStarted
from app.config import settings

@post
async def handle(req: Request) -> Response:
    incoming = await verify(req, secret=settings.stripe_signing_secret)
    # incoming.name (string), .body (bytes), .json (dict)
    match incoming.name:
        case "customer.subscription.created":
            await SubscriptionStarted(
                organization_id=...,
                customer_id=incoming.json["customer"],
            ).emit()
        case _:
            ...
    return Response(status=204)
```

`verify` checks HMAC + timestamp and returns an `IncomingWebhook` with the parsed JSON. A missing or stale signature raises `Unauthorized` (401). An invalid body raises `Unauthorized` too — clients shouldn't be able to tell signature failure from body-parse failure.

## Testing

Use `captured_webhooks` to assert on what would have been delivered without firing real HTTP:

```python
from causeway.testing import captured_webhooks

async def test_creating_customer_notifies_slack(client):
    async with captured_webhooks() as deliveries:
        await client.post("/customers", json={"email": "a@b"})
    assert len(deliveries) == 1
    assert deliveries[0].url == "https://slack.example"
    assert deliveries[0].event_name == "customer.created"
```

The block short-circuits the task adapter — no `_deliver.enqueue` runs, no httpx requests. The captured list reflects post-`where`-filter matches.

## Listening for delivery failures

Causeway emits `WebhookDeliveryFailed` after a delivery exhausts its retry budget. Subscribe to it from a listener:

```python
# app/listeners/webhook_health.py
from causeway.webhooks import WebhookDeliveryFailed

@WebhookDeliveryFailed.listen
async def disable_persistently_failing(p: WebhookDeliveryFailed) -> None:
    if p.attempts >= 10:
        # Disable the endpoint in your WebhookStore...
        ...
```

`WebhookDeliveryFailed` is `webhook = False` so it doesn't itself fan out as a webhook — otherwise a broken endpoint would cascade into more failure deliveries.

## File layout

```
app/
  events/
    customer_created.py                    # class CustomerCreated(Event): webhook = True; ...
  subscribers/                             # static outbound targets
    slack.py                               # Subscriber(url=..., events=[CustomerCreated])
    datadog.py
  listeners/
    webhook_health.py                      # @WebhookDeliveryFailed.listen
  routes/(public)/webhooks/
    stripe.py                              # incoming receiver
```

## Migrating from the 0.1 webhooks API

The 0.1 API was `webhooks.register_endpoint(...)` + `webhooks.send(endpoint_id, event_name, payload)`. Both are gone.

| 0.1                                                                                   | 0.2+                                                                           |
| ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `webhooks.register_endpoint("ep", url=..., secret=..., events=[...])` in startup hook | `Subscriber(url=..., secret=..., events=[Cls])` in `app/subscribers/<name>.py` |
| `webhooks.send("ep", event_name, payload)`                                            | `await EventClass(...).emit()`                                                 |
| `webhooks.disable_endpoint("ep")`                                                     | Delete the subscriber file (static) / `store.unsubscribe(id)` (dynamic)        |
| `webhooks.delivery_status(id)`                                                        | `task_adapter.status(id)`                                                      |
| `Webhooks.send` Protocol method                                                       | gone — delivery is `@task`                                                     |
