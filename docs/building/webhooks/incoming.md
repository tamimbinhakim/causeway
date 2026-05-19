# Verifying incoming webhooks

Every backend that integrates with a third party — Stripe, GitHub, Slack, Shopify — receives webhooks from them. Every vendor signs the payload, every signature scheme is timestamp + HMAC over the body, and every team rewrites the verifier wrong the first time. Causeway ships the helpers so you don't.

## Verifying a request signed by Causeway

```python
from causeway import post, verify_signature
from causeway.errors import Unauthorized

@post
async def receive(req: Request) -> dict[str, str]:
    body = await req.body()
    verify_signature(
        SECRET,
        body,
        req.headers.get("x-causeway-signature"),
        req.headers.get("x-causeway-timestamp"),
    )
    event = msgspec.json.decode(body)
    await handle(event)
    return {"ok": "true"}
```

Two failure modes, both surface as `401`:

- **Missing or malformed signature** — header absent, version prefix wrong.
- **Stale timestamp** — outside the configured skew window (default 300s).

## Adapting to other vendors

The signature format is the same shape across most B2B APIs — only the headers differ. The helpers accept arbitrary header values, so adapting to Stripe or GitHub is a few lines:

```python
# Stripe
verify_signature(STRIPE_SECRET, body, req.headers.get("stripe-signature"), ts)

# GitHub
verify_signature(GITHUB_SECRET, body, req.headers.get("x-hub-signature-256"), ts)
```

For vendors whose signature input isn't `f"{ts}.{body}"`, write a small adapter around `hmac.compare_digest` — the helpers don't try to cover every variant.

## Replay protection

`max_skew_seconds` (default 300s, ±5 minutes) is the window during which a captured request can be replayed before the verifier rejects it. Lower if your clock sync is reliable; don't go below 60s in practice (NTP and Lambda cold starts can drift more than that).

## Mounting via the contract

If you registered `InMemoryWebhooks` (or another adapter), the contract method `verify_incoming` is the same call wrapped in a `Webhooks` instance — useful when the secret lookup is per-endpoint:

```python
from causeway.contracts import Webhooks
from causeway.plugins import registered

webhooks: Webhooks = next(a for a in registered() if isinstance(a, Webhooks))
body = webhooks.verify_incoming(req, secret=endpoint.secret)
```
