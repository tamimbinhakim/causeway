# `@provide`

Declare a request-scoped DI provider inside a `_scope.py`.

```python
# src/app/routes/users/_scope.py
from causeway import provide

@provide("db")
async def get_session():
    async with session_factory() as s:
        yield s
```

## Signature

```python
provide(name: str) -> Callable[[Callable], Callable]
```

The decorator stamps `__causeway_provide__ = name` on the function so the file router can collect it.

## Rules

- `name` must be a non-empty string. Two `@provide("db")` declarations in the same `_scope.py` file raise `TypeError` at boot.
- The provider itself can be sync, async, a sync generator, or an async generator. Generators get teardown after the response.
- Providers compose by subtree. The inner-most provider for a given name wins; outer providers are inherited.

## Binding in a handler

```python
from typing import Annotated
from causeway import get

@get
async def show(id: UUID, db: Annotated[Session, get_session]) -> User:
    return await db.get(User, id)
```

The file router rewrites `Annotated[Session, get_session]` into `dyadpy.Depends(get_session)` automatically.

## See also

- [Scopes](../../building/routing/scopes.md)
- [`_scope.py`](../file-conventions/scope-py.md)
