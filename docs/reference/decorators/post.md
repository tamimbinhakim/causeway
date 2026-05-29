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
post(*, refreshes: str | Iterable[str] = ()) -> Callable[[Callable], Callable]
```

Bare decorator by default. The optional `refreshes` kwarg stores route-contract metadata on the handler as `__causeway_contract__["refreshes"]`.

```python
@post(refreshes=("GET /users/$id", "GET /users"))
async def screen(id: UUID) -> Screening: ...
```

The client runtime refreshes those route keys after a successful mutation. Failed mutations do not refresh.

## Status code defaults

- Function named `create` → `201 Created`.
- Anything else → `200 OK`.
- Returning `None` → `204 No Content`.

For explicit control, take a `causeway.Context` parameter and call `ctx.set_status(...)`.

## See also

- [Methods](../../backend/methods.md)
- [Params and body](../../backend/params-and-body.md)
- [`@get`](./get.md), [`@put`](./put.md), [`@patch`](./patch.md), [`@delete`](./delete.md)
