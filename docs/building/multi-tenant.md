# Multi-tenancy

B2B SaaS — and most internal tools — are workspace-scoped. Causeway has everything you need for that out of the box: request-scoped DI via `_scope.py` plus inheritance through the routes tree. The pattern below is the canonical way to plug a tenant in once and have every downstream provider automatically receive it.

## The pattern

```python
# src/app/routes/_scope.py
from typing import Annotated
from causeway import provide
from app.lib.auth import parse_token

@provide("tenant")
async def get_tenant(req) -> str:
    """Resolve the calling tenant from the bearer token.

    Runs once per request; downstream providers that depend on ``tenant``
    share the same instance.
    """
    user = await parse_token(req.headers.get("authorization", ""))
    return user.org_id


@provide("db")
async def get_session(tenant: Annotated[str, get_tenant]):
    async with session_factory() as s:
        async with TenantSession(s, org_id=tenant) as scoped:
            yield scoped
```

`TenantSession` is a small wrapper around the SQLModel/SQLAlchemy session that binds every query to a `WHERE org_id = :tenant` clause. The point is: the route doesn't think about tenancy. The provider does it once.

## Why this works

Causeway resolves providers in dependency order. `db` declares `tenant: Annotated[str, get_tenant]`, so `get_tenant` runs first and its result is threaded into `get_session`. The route's handler sees a tenant-scoped session and nothing else.

```python
# src/app/routes/users.py
@get
async def list_users(db: Annotated[Session, get_session]) -> list[User]:
    # The query is auto-scoped — no `where org_id == tenant` here.
    return await db.execute(select(User)).scalars().all()
```

## Overriding in tests

`app.override(get_tenant, lambda: "test-org-1")` swaps the provider for a single test:

```python
async def test_list_users_scoped_to_tenant(app):
    with app.override(get_tenant, lambda req: "org-1"):
        resp = await client.get("/users")
        assert all(u.org_id == "org-1" for u in resp.json())
```

## When *not* to do this

- **Single-tenant apps.** If there's only ever one customer, the indirection just slows the team down.
- **Admin routes that span tenants.** Put them under a subtree (`routes/(admin)/`) with a different `_scope.py` that resolves a "superuser" session instead of a tenant-scoped one.
- **Background tasks.** Tasks don't run inside a request, so they can't read the tenant off the header. Pass it as a task argument or pull it from the job's payload.

## What stays out of the framework

There is no `@tenant_required` decorator, no `Tenant` base class, no opinionated org/user model. Multi-tenancy is one provider + one session wrapper. The framework gives you the composition; the domain model is yours.
