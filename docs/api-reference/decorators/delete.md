# `@delete`

Register a function as a `DELETE` handler.

```python
from causeway import delete

@delete
async def remove(id: UUID) -> None: ...
```

## Signature

```python
delete(handler: Callable) -> Callable
```

Bare decorator. Stamps `__causeway_method__ = "DELETE"`.

## Status code defaults

A `@delete` handler that returns `None` produces `204 No Content`. Returning a struct gives `200 OK`.

## See also

- [Methods](../../building/handlers/methods.md)
- [`@get`](./get.md), [`@post`](./post.md), [`@put`](./put.md), [`@patch`](./patch.md)
