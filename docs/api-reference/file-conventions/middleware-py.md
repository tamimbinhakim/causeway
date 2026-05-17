# `_middleware.py`

Per-subtree middleware declaration. The discovery walker collects every `_middleware.py` it encounters and composes them by depth.

```python
# src/app/routes/_middleware.py
from causeway import Middleware, guard
from causeway.middleware import Request, Response


@guard
async def require_login(req): ...


class Timing(Middleware):
    async def __call__(self, req: Request, call_next): ...


middleware = [require_login, Timing()]
```

## Rules

- The file must be named exactly `_middleware.py`.
- It must export a list named `middleware`.
- Each entry must be:
  - a `Middleware` instance (class with `async __call__(self, req, call_next)`), **or**
  - a `@guard`-decorated function.

Anything else raises `TypeError` at boot.

## Composition order

For a request to `/users/{id}`:

```
app-level middleware →
  routes/_middleware.py →
    routes/users/_middleware.py →
      handler
```

Response unwinds in reverse. Inner-most middleware sees the response first; outer-most sees it last.

## Scope

A `_middleware.py` applies to **every route in the current subtree**, recursively. To scope tighter:

- Move it deeper into the tree (e.g. `routes/admin/_middleware.py` only affects `/admin/*`).
- Wrap a subset in a [route group](./group.md) (`(admin)/_middleware.py` affects only routes inside `(admin)`).

## See also

- [Middleware](../../building/routing/middleware.md)
- [`@guard`](../decorators/guard.md)
- [`Middleware`](../classes/Middleware.md)
