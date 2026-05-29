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
patch(*, refreshes: str | Iterable[str] = ()) -> Callable[[Callable], Callable]
```

Bare decorator by default. The optional `refreshes` kwarg stores route-contract metadata on the handler as `__causeway_contract__["refreshes"]`.

## See also

- [Methods](../../backend/methods.md)
- [`@get`](./get.md), [`@post`](./post.md), [`@put`](./put.md), [`@delete`](./delete.md)
