# Middleware

Per-subtree request wrappers. One `_middleware.py` at the root of a subtree wraps every route below it — no decorator stack on every handler.

## The convention

```python
# src/app/routes/_middleware.py
from causeway import Middleware
from causeway.middleware import Request, Response


class RequestId(Middleware):
    async def __call__(self, req: Request, call_next):
        rid = req.headers.get("x-request-id") or new_id()
        req.state.request_id = rid
        resp: Response = await call_next(req)
        resp.headers["x-request-id"] = rid
        return resp


middleware = [RequestId()]
```

Three rules:

1. The file is named `_middleware.py`.
2. It exports a list named `middleware`.
3. Each entry is either a `Middleware` instance or a `@guard`-decorated function.

The discovery walker collects every `_middleware.py` it encounters and composes them by depth.

## Composition order

For a request to `/users/123`:

```
app-level middleware (RequestIdMiddleware) →
  routes/_middleware.py →
    routes/users/_middleware.py →
      handler
```

Response unwinds in reverse: leaf middleware exits first, root last. The inner-most middleware sees the response first; the outer-most sees it last.

> **Good to know.** Want a guard to run before everything? Put it in `routes/_middleware.py`. Want it to be the last thing before the handler? Put it in the leaf `_middleware.py`.

## Two flavors

### Class-based `Middleware`

Full request/response control. Implements `async __call__(req, call_next)`. The Starlette `Request` and `Response` objects are the same ones Starlette uses everywhere.

```python
from causeway import Middleware
from causeway.middleware import Request, Response
import time


class Timing(Middleware):
    async def __call__(self, req: Request, call_next):
        start = time.perf_counter()
        resp: Response = await call_next(req)
        resp.headers["x-elapsed-ms"] = f"{(time.perf_counter() - start) * 1000:.1f}"
        return resp


middleware = [Timing()]
```

### `@guard` — lightweight, function-style

Guards run **before** the handler. Raise to short-circuit:

```python
from causeway import guard

@guard
async def require_admin(req):
    user = await current_user(req)
    if not user or not user.is_admin:
        raise PermissionError("admin only")


middleware = [require_admin]
```

The error renderer translates common exceptions automatically:

| Exception              | Rendered status |
| ---------------------- | --------------- |
| `PermissionError`      | 403             |
| `LookupError`          | 404             |
| `causeway.errors.*`    | as declared     |
| anything else          | 500 (generic)   |

> **Good to know.** Guards are for "should this request even reach the handler?" If you need to mutate the request or response, use a class-based `Middleware`.

## Mixing both in one file

```python
# src/app/routes/(admin)/_middleware.py
from causeway import Middleware, guard


@guard
async def require_admin(req): ...


class AuditLogger(Middleware):
    async def __call__(self, req, call_next): ...


middleware = [require_admin, AuditLogger()]
```

The router runs guards first, then enters the class-middleware chain.

## Where it lives matters

| Place                             | Applies to                  |
| --------------------------------- | --------------------------- |
| `routes/_middleware.py`           | Every route in the app      |
| `routes/users/_middleware.py`     | Only `/users/*`             |
| `routes/(admin)/_middleware.py`   | Only routes inside `(admin)`|
| `routes/billing/_middleware.py`   | Only `/billing/*`           |

Use [route groups](./route-groups.md) to scope middleware to a slice of the tree without changing URLs.

## App-level middleware

For wrappers that should apply even before the route table is hit, register at app level via `plugins.py`. Examples: CORS, OTel ASGI middleware, request body size limits. These are framework-wide; the per-subtree convention is for per-route concerns.

## Common patterns

**Auth tier per group:**
```
routes/(public)/_middleware.py     →    middleware = []
routes/(user)/_middleware.py       →    middleware = [require_login]
routes/(admin)/_middleware.py      →    middleware = [require_admin]
```

**Cross-cutting concerns at root:**
```
routes/_middleware.py              →    middleware = [RequestId(), Timing()]
```

**Per-feature scope:**
```
routes/billing/_middleware.py      →    middleware = [verify_stripe_signature]
```

## Caveats

- Every entry in `middleware = [...]` must be a `Middleware` instance or a `@guard`-decorated function. Anything else raises `TypeError` at boot.
- The `middleware` name is required. Calling the list `mws = [...]` won't be picked up.
- Middleware doesn't see route params — those bind inside the handler. To read the param in a guard, parse the URL yourself or do the check inside the handler.

## Next

- [Scopes](./scopes.md) — request-scoped DI providers.
- [Route groups](./route-groups.md) — the most common way to limit middleware reach.
- [Reference — `Middleware`](../../api-reference/classes/Middleware.md)
- [Reference — `@guard`](../../api-reference/decorators/guard.md)
