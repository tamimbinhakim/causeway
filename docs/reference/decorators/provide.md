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

The file router rewrites `Annotated[Session, get_session]` into `causeway.Depends(get_session)` automatically.

`from __future__ import annotations` (PEP 563) at the top of the route file is supported — the binder resolves string annotations via `inspect.signature(..., eval_str=True)`. Provider params can appear in any position; the rewriter splices them in as keyword-only, so a signature like `(db: Annotated[Session, get_session], id: UUID)` is fine even though `id` has no default.

## See also

- [Scopes](../../backend/scopes.md)
- [`_scope.py`](../file-conventions/scope-py.md)
