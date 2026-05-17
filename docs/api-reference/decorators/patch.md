# `@patch`

Register a function as a `PATCH` handler.

```python
from causeway import patch

@patch
async def update(id: UUID, data: UserPatch) -> User: ...
```

## Signature

```python
patch(handler: Callable) -> Callable
```

Bare decorator. Stamps `__causeway_method__ = "PATCH"`.

## See also

- [Methods](../../building/handlers/methods.md)
- [`@get`](./get.md), [`@post`](./post.md), [`@put`](./put.md), [`@delete`](./delete.md)
