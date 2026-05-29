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
delete(*, refreshes: str | Iterable[str] = ()) -> Callable[[Callable], Callable]
```

Bare decorator by default. The optional `refreshes` kwarg stores route-contract metadata on the handler as `__causeway_contract__["refreshes"]`.

## Status code defaults

A `@delete` handler that returns `None` produces `204 No Content`. Returning a struct gives `200 OK`.

## See also

- [Methods](../../backend/methods.md)
- [`@get`](./get.md), [`@post`](./post.md), [`@put`](./put.md), [`@patch`](./patch.md)
