# `@guard`

Lightweight middleware that runs before the handler. Raise to short-circuit.

```python
from causeway import guard

@guard
async def require_admin(req):
    user = await current_user(req)
    if not user or not user.is_admin:
        raise PermissionError("admin only")
```

## Signature

```python
guard(fn: Callable[[Request], Awaitable[None]]) -> Callable
```

`fn` receives the Starlette `Request`. Returns `None`. Raises to short-circuit.

## Behavior

- Stamps `__causeway_guard__ = True` on the function so the discovery walker recognizes it.
- Listed in a `_middleware.py`'s `middleware = [...]` to install it.
- Runs in order before any class `Middleware` and before the handler.
- A raised exception flows to the error renderer.

## Exception → status mapping

| Raised in guard     | Rendered status |
| ------------------- | --------------- |
| `PermissionError`   | 403 `forbidden` |
| `LookupError`       | 404 `not_found` |
| `causeway.errors.*` | as declared     |
| anything else       | 500 `internal`  |

## Installing

```python
# src/app/routes/(admin)/_middleware.py
from causeway import guard

@guard
async def require_admin(req): ...

middleware = [require_admin]
```

## See also

- [Middleware](../../building/routing/middleware.md)
- [`Middleware`](../classes/Middleware.md) — for full request/response control.
- [Errors](../../building/handlers/errors.md)
