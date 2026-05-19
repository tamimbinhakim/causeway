# Verifying incoming webhooks

Every backend that integrates with a third party — Stripe, GitHub, Slack, Shopify — receives webhooks from them. Every vendor signs the payload, every signature scheme is timestamp + HMAC over the body, and every team rewrites the verifier wrong the first time. Causeway ships the helpers so you don't.

## The high-level path: `verify()`

For webhooks signed in causeway's own format (or other Stripe-style HMAC-SHA256 vendors), use `verify`:

```python
# app/routes/(public)/webhooks/stripe.py
from causeway import post
from causeway.webhooks import verify
from app.events.subscription_started import SubscriptionStarted
from app.config import settings

@post("/")
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

`verify` does three things atomically:

1. Reads the request body (calls `await req.body()` if Starlette-style).
2. Verifies HMAC signature + timestamp (delegates to `verify_signature`).
3. Parses the body as JSON and returns an `IncomingWebhook` with the event name, raw bytes, and parsed dict.

A missing/malformed signature, stale timestamp, or invalid JSON all surface as `Unauthorized` (401). Clients can't tell the failure modes apart — that's by design.

## The low-level path: `verify_signature()`

For vendors with a different header layout or signature input, do the verification by hand:

```python
from causeway import post
from causeway.webhooks import verify_signature
from causeway.errors import Unauthorized

@post("/")
async def receive(req: Request) -> dict[str, str]:
    body = await req.body()
    verify_signature(
        STRIPE_SECRET,
        body,
        req.headers.get("stripe-signature"),
        req.headers.get("stripe-timestamp"),
    )
    event = msgspec.json.decode(body)
    await handle(event)
    return {"ok": "true"}
```

Two failure modes, both surface as `401`:

- **Missing or malformed signature** — header absent, version prefix wrong.
- **Stale timestamp** — outside the configured skew window (default 300s).

## Adapting to other vendors

The HMAC pattern is the same across most B2B APIs — only header names differ. Pass the vendor's header values straight through:

```python
# Stripe
verify_signature(STRIPE_SECRET, body, req.headers.get("stripe-signature"), ts)

# GitHub
verify_signature(GITHUB_SECRET, body, req.headers.get("x-hub-signature-256"), ts)
```

For vendors whose signature input isn't `f"{ts}.{body}"`, write a small adapter around `hmac.compare_digest` — the helpers don't try to cover every variant.

## Replay protection

`max_skew_seconds` (default 300s, ±5 minutes) is the window during which a captured request can be replayed before the verifier rejects it. Lower if your clock sync is reliable; don't go below 60s in practice (NTP and Lambda cold starts can drift more than that).

## Bridging incoming to your event stream

A common pattern is to translate a verified incoming webhook into one of your own `Event` classes and re-emit it internally:

```python
@post("/")
async def handle(req: Request) -> Response:
    incoming = await verify(req, secret=settings.stripe_signing_secret)
    if incoming.name == "customer.subscription.created":
        await SubscriptionStarted(
            organization_id=settings.org_id,
            customer_id=incoming.json["customer"],
        ).emit()
    return Response(status=204)
```

This keeps third-party signals first-class in your event system — listeners and subscribers don't care whether the trigger was internal or external.

## Why this is minimal

There's no file-routed dispatch for incoming webhooks. Most apps have **one receiver per provider** (one Stripe handler, one GitHub handler), and they branch internally. File-routing the inside would be over-engineering for what's usually a `match incoming.name:` block.
