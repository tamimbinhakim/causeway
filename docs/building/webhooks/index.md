# Webhooks (outgoing)

The `Webhooks` contract covers outgoing delivery with HMAC signing, exponential backoff, and per-delivery state tracking. Causeway ships `InMemoryWebhooks` as the reference adapter — fine for tests, demos, and single-process apps; durable delivery lives in sibling plugins like `causeway-webhooks-pg`.

## Setup

```python
# src/app/plugins.py
from causeway import register, InMemoryWebhooks

register(InMemoryWebhooks())
```

## Registering endpoints

Each receiver gets an endpoint id, URL, and a secret. The secret is what the signature is computed against — store it server-side, never log or echo it:

```python
from causeway import new_secret
from causeway.contracts import Webhooks
from causeway.plugins import registered

webhooks: Webhooks = next(a for a in registered() if isinstance(a, Webhooks))
await webhooks.register_endpoint(
    "team-42",
    url="https://example.com/hooks",
    secret=new_secret(),
    events=["user.created", "user.deleted"],
)
```

## Sending

```python
await webhooks.send(
    "team-42",
    event="user.created",
    payload={"id": "u_123", "email": "ada@example.com"},
    idempotency_key="user.created:u_123",
)
```

`idempotency_key` deduplicates the *delivery* — calling `send` twice with the same key returns the same delivery id and only fires the webhook once. Use it when the same business event might be emitted from two code paths.

## Signing format

The reference adapter signs with Stripe-style HMAC-SHA256 over `f"{timestamp}.{body}"`:

```
X-Causeway-Signature: v1,<hex(hmac_sha256(secret, f"{ts}.{body}"))>
X-Causeway-Timestamp: <unix-seconds>
```

The format is intentionally a copy of what Stripe popularized — well-understood, easy to verify, no novel cryptography.

## Retry schedule

`InMemoryWebhooks` walks the retry table on transport failure or non-2xx response: 10s, 60s, 5m, 30m, 4h. Five attempts over roughly five hours. Endpoints stay registered through the schedule; explicit `disable_endpoint(id)` is the way to take a misbehaving receiver out of rotation.

## Inspecting deliveries

```python
status = await webhooks.delivery_status(delivery_id)
# WebhookDelivery(delivery_id="...", state="delivered", attempts=2, last_error=None, ...)
```

`state` is one of `pending`, `in_flight`, `delivered`, `failed`.
