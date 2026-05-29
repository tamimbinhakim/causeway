# `@get`

Register a function as a `GET` handler. The URL comes from the file location; the decorator only binds the method.

```python
from causeway import get

@get
async def show(id: UUID) -> User: ...
```

## Signature

```python
get(handler: Callable) -> Callable
get(*, refreshes: str | Iterable[str] = ()) -> Callable[[Callable], Callable]
```

Bare decorator by default. The optional `refreshes` kwarg stores route-contract metadata on the handler as `__causeway_contract__["refreshes"]`.

`refreshes` is mostly useful on mutation methods; it is accepted here for a consistent decorator shape.

## Rules

- One method decorator per function. `@get` + `@post` on the same function raises `TypeError` at import time.
- Two `@get`-decorated handlers in one file (same URL, same method) raise at boot — pick one or split into separate files.
- A `@get` handler that returns `None` produces `204 No Content`.

## See also

- [Defining routes](../../backend/routing.md)
- [Methods](../../backend/methods.md)
- [`@post`](./post.md), [`@put`](./put.md), [`@patch`](./patch.md), [`@delete`](./delete.md)
