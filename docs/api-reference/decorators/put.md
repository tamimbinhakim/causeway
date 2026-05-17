# `@put`

Register a function as a `PUT` handler.

```python
from causeway import put

@put
async def replace(id: UUID, data: User) -> User: ...
```

## Signature

```python
put(handler: Callable) -> Callable
```

Bare decorator. Stamps `__causeway_method__ = "PUT"`.

## See also

- [Methods](../../building/handlers/methods.md)
- [`@get`](./get.md), [`@post`](./post.md), [`@patch`](./patch.md), [`@delete`](./delete.md)
