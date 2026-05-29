# `Depends`

DI marker for handler parameters.

```python
from causeway import Depends

async def get_db(): ...

@get
async def show(id: UUID, db = Depends(get_db)) -> User: ...
```

> **Good to know.** In Causeway, the recommended way to bind a scoped provider is via `Annotated[T, provider]` — the file router rewrites that into `Depends(provider)` automatically. Use raw `Depends` only when you're working outside the `_scope.py` convention.

## Signature

```python
Depends(provider: Callable) -> Any
```

The provider can be sync, async, a sync generator, or an async generator. Generators get teardown after the response.

## See also

- [Scopes](../../backend/scopes.md)
- [`@provide`](../decorators/provide.md)
- [Params and body](../../backend/params-and-body.md)
