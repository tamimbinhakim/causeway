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
put(*, refreshes: str | Iterable[str] = ()) -> Callable[[Callable], Callable]
```

Bare decorator by default. The optional `refreshes` kwarg stores route-contract metadata on the handler as `__causeway_contract__["refreshes"]`.

## See also

- [Methods](../../backend/methods.md)
- [`@get`](./get.md), [`@post`](./post.md), [`@patch`](./patch.md), [`@delete`](./delete.md)
