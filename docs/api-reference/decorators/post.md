# `@post`

Register a function as a `POST` handler. The URL comes from the file location.

```python
from causeway import post

@post
async def create(data: NewUser) -> User: ...
```

## Signature

```python
post(handler: Callable) -> Callable
```

Bare decorator — no arguments. Returns the function stamped with `__causeway_method__ = "POST"`.

## Status code defaults

- Function named `create` → `201 Created`.
- Anything else → `200 OK`.
- Returning `None` → `204 No Content`.

For explicit control, take a `causeway.Context` parameter and call `ctx.set_status(...)`.

## See also

- [Methods](../../building/handlers/methods.md)
- [Params and body](../../building/handlers/params-and-body.md)
- [`@get`](./get.md), [`@put`](./put.md), [`@patch`](./patch.md), [`@delete`](./delete.md)
