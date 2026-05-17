# Scopes

A `_scope.py` file is the subtree's **DI + lifespan declaration**. It does two things:

1. Declares request-scoped providers via `@provide(...)`.
2. Optionally exposes scope-scoped lifespan hooks (`startup()` / `shutdown()`).

## Providers

```python
# src/app/routes/users/_scope.py
from causeway import provide
from app.lib.db import session_factory


@provide("db")
async def get_session():
    async with session_factory() as s:
        yield s
```

Any handler under `routes/users/` can now take a `db` parameter:

```python
# src/app/routes/users/[id].py
from typing import Annotated
from causeway import get

@get
async def show(id: UUID, db: Annotated[Session, get_session]) -> User:
    return await db.get(User, id)
```

Three rules:

1. The provider is a plain function — sync, async, generator, or async generator. Generators that `yield` get teardown after the response.
2. Each call creates a fresh instance — providers are **request-scoped**, not module-scoped.
3. The handler binds the provider via `Annotated[T, provider]` — the file router rewrites that into `dyadpy.Depends(provider)` automatically.

## Composition

Scopes inherit. A provider declared in `routes/_scope.py` is visible everywhere below; a provider declared in `routes/admin/_scope.py` is only visible under `/admin/*`.

When two scopes declare a provider under the same name, **the inner-most wins**:

```
routes/_scope.py                @provide("db")  →  postgres session
routes/admin/_scope.py          @provide("db")  →  read-replica session
```

A handler in `routes/admin/stats.py` that takes `db: Annotated[..., get_session]` gets the read-replica.

## Lifespan hooks

A `_scope.py` can also export `startup()` / `shutdown()` for things that should open once per process and close cleanly:

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

The framework fires `startup()` hooks in discovery order on app boot, and `shutdown()` hooks in **reverse** discovery order on shutdown.

> **Good to know.** Lifespan hooks are useful when a resource is expensive to construct but should be lazy — only open the Stripe client if at least one billing route exists. If you want a process-wide resource regardless of subtree, put the startup in `src/app/lifespan.py` or a plugin's `startup`.

## Provider shapes

```python
# Sync function — value computed per-request
@provide("now")
def get_now() -> datetime:
    return datetime.now(UTC)


# Async function — same, but awaited
@provide("user")
async def get_user(req) -> User:
    return await load_user(req.headers["authorization"])


# Generator with teardown — yields the value, the rest runs after the response
@provide("db")
async def get_session():
    async with session_factory() as s:
        yield s    # cleanup happens after the response is sent
```

## Why named providers

Providers bind by **name** plus identity. `@provide("db")` says "this function is the `db` provider for this subtree." If you have two providers that produce the same Python type (two different session pools, two different storage adapters), the name disambiguates.

> **Watch out.** Two `@provide("db")` declarations in the same `_scope.py` file raise at boot — names must be unique within a single scope file. Different files can override by re-declaring.

## Overriding providers in tests

```python
from causeway.testing import TestApp

app = TestApp.from_routes("src/app/routes")

async with app.override(get_session, fake_session):
    r = await app.post("/users", json={"name": "ada"})
```

The override uses the same scope machinery as production — there's no separate "test injection" path to learn. See [Testing](../testing/index.md).

## Common patterns

**Per-feature pool:**
```
routes/_scope.py                @provide("db")          postgres session
routes/(admin)/_scope.py        @provide("db")          read-replica session
routes/billing/_scope.py        @provide("stripe")      stripe client
```

**Request-scoped current user:**
```
routes/(user)/_scope.py         @provide("current_user") parses JWT from header
```

**Idempotency keys for write routes:**
```
routes/users/_scope.py          @provide("idem")        looks up Idempotency-Key header
```

## Caveats

- A provider that depends on another provider is supported — Causeway hands them to `dyadpy.Depends`, which composes naturally.
- Providers can't depend on themselves (cycle detection happens at request time and raises).
- A `_scope.py` that doesn't export `startup` / `shutdown` is fine; both are optional.

## Next

- [Middleware](./middleware.md) — guards and wrappers next to scopes.
- [Reference — `provide`](../../api-reference/decorators/provide.md)
- [Reference — file conventions](../../api-reference/file-conventions/scope-py.md)
