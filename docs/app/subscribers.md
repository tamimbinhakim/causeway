# Subscribers

A **subscriber** is an external HTTP endpoint that wants to receive a webhook when one of your [events](./events.md) fires. Two flavors:

- **Static `Subscriber`** — declared in `app/subscribers/<name>.py` at build time. URL/secret come from config. Used for fixed integrations.
- **Dynamic subscription** — created at runtime through a `WebhookStore` plugin. Used for end-user-supplied URLs.

Both flavors plug into the same `Event.emit()` fan-out.

## Static `Subscriber`

The simplest case: you ship the app, you know the URL at build time.

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

Discovery walks `app/subscribers/*.py` at boot, importing each module. The module-level `Subscriber(...)` instance registers itself against each event class's `_subscribers` list via `__post_init__`.

**One subscriber per file.** The file name becomes the subscriber id (`slack`). Removing the subscriber = deleting the file.

## Filtering with `where`

A subscriber can carry a `where` dict that exact-matches event fields. Only events whose values match every key get delivered:

```python
# Tenant scoping:
prod_acme = Subscriber(
    url="https://acme.example/hooks",
    secret=settings.acme_secret,
    events=[CustomerCreated],
    where={"organization_id": ACME_ORG_ID},
)

# Region + environment:
us_east_prod = Subscriber(
    url="https://us-monitor.example",
    secret=settings.monitor_secret,
    events=[OrderShipped],
    where={"region": "us-east", "env": "prod"},
)
```

Rules:

- `where=None` (or omitted) → match every event of the subscribed types.
- Multiple keys AND together; there's no `or` operator (use multiple subscribers).
- Unknown keys (field not declared on the event class) → `ValueError` at module import. Catches typos at boot, not at emit.
- Equality is JSON-roundtrip permissive: `UUID("...")` and its string form compare equal.

The `where` shape is identical for static and dynamic subscribers, so logic that builds filters works either way.

## Dynamic subscriptions

When customers paste their own webhook URL into a settings UI, you need runtime storage. That's what `WebhookStore` is for:

```python
# app/routes/settings/webhooks.py
@post
async def create_subscription(req: Request, *, store: WebhookStore) -> Response:
    secret = new_secret()
    endpoint_id = await store.subscribe(
        url=req.json["url"],
        secret=secret,
        events=[CustomerCreated.wire_name, OrderShipped.wire_name],  # strings
        where={"organization_id": current_user(req).org_id},
    )
    # Return the secret ONCE — never store or log it plaintext after this.
    return Response.json({"id": endpoint_id, "secret": secret})
```

Dynamic subscribers reference events by **wire name string** (`"customer.created"`) instead of the class. The public API can't accept Python classes — external callers don't import your app's code.

### Available stores

| Store                                           | Durability    | Suitable for                |
| ----------------------------------------------- | ------------- | --------------------------- |
| `InMemoryWebhookStore` (built-in)               | Process-local | Tests, single-process demos |
| `causeway-webhooks-pg` (planned sibling plugin) | Postgres      | Production multi-tenant     |

`InMemoryWebhooks` (the lifecycle adapter) does **not** implement `WebhookStore` — its `subscribe()` raises `NotImplementedError`. The in-memory adapter can't honestly persist subscriptions across restarts; pretending to would be a footgun.

## What happens on emit

```python
await CustomerCreated(organization_id=org.id, id=u.id, email=u.email).emit()
```

1. Run every in-process `@CustomerCreated.listen` listener (awaited, concurrent).
2. If `CustomerCreated.webhook = True`, walk `CustomerCreated._subscribers` + dynamic-store rows, apply each subscriber's `where` filter, and enqueue one `_deliver` task per match.
3. Return an `EmitResult` listing the enqueued task ids.

Listeners are awaited; deliveries are not. The caller never blocks on outbound HTTP.

## Inspecting registrations

For debugging or admin UIs:

```python
from causeway.events import all_events, webhookable_events
from app.events.customer_created import CustomerCreated

# All events, by wire name:
for wire_name, cls in all_events().items():
    print(wire_name, cls.__name__)

# Only events that can fan out to webhooks:
events = webhookable_events()  # list[type[Event]]

# Subscribers for a specific event:
for sub in CustomerCreated._subscribers:
    print(sub.url, sub.where)
```

## Testing

`captured_webhooks()` records what would have been delivered without firing real HTTP or enqueueing any tasks:

```python
from causeway.testing import captured_webhooks

async def test_creating_customer_notifies_each_subscriber(client):
    async with captured_webhooks() as deliveries:
        await client.post("/customers", json={"email": "a@b"})
    urls = sorted(d.url for d in deliveries)
    assert urls == ["https://datadog.example", "https://slack.example"]
```

Each `CapturedDelivery` has `subscriber_id`, `url`, `event_name`, `event` (the typed instance), and `where` (the filter the subscriber declared, for diagnostics).

## File layout

```
app/
  events/
    customer_created.py                   # webhook = True
    payment_failed.py
    order_shipped.py
  subscribers/                            # one file per subscriber
    slack.py                              # static, all customer events
    datadog.py                            # static, errors only
    partner_acme.py                       # static, scoped to ACME's org
```

Discovery walks all three of `events/`, `listeners/`, `subscribers/` at boot. Missing folders are skipped silently.
