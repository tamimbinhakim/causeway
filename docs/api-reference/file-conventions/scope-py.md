# `_scope.py`

Per-subtree DI providers and optional lifespan hooks.

```python
# src/app/routes/billing/_scope.py
from causeway import provide
from stripe import StripeClient

_stripe: StripeClient | None = None


async def startup():
    global _stripe
    _stripe = StripeClient(api_key=settings.stripe_key.get_secret_value())


async def shutdown():
    if _stripe is not None:
        await _stripe.aclose()


@provide("stripe")
async def get_stripe() -> StripeClient:
    assert _stripe is not None
    return _stripe
```

## What it exports

| Name                                      | Purpose                                                                     |
| ----------------------------------------- | --------------------------------------------------------------------------- |
| `startup`                                 | Optional `async def` — fires when the app starts.                           |
| `shutdown`                                | Optional `async def` — fires when the app stops (reverse-of-startup order). |
| Any `@provide("name")`-decorated function | Becomes a request-scoped DI provider.                                       |

## Rules

- File must be named exactly `_scope.py`.
- Two `@provide("db")` declarations in the same file raise `TypeError` at boot — names must be unique within a single scope file.
- Different `_scope.py` files can override the same name — the inner-most (deepest in the tree) wins.

## Binding a provider in a handler

```python
from typing import Annotated
from causeway import get

@get
async def show(id: UUID, db: Annotated[Session, get_session]) -> User: ...
```

The file router rewrites `Annotated[Session, get_session]` into `causeway.Depends(get_session)` at boot.

## Lifespan order

- `startup` fires in discovery order (root scope first).
- `shutdown` fires in reverse-of-discovery order (root scope last).

## See also

- [Scopes](../../building/routing/scopes.md)
- [`@provide`](../decorators/provide.md)
