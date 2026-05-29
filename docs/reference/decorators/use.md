# `@use`

Attach middleware or guards to one handler.

```python
from causeway import post, require_permission, use

@post(refreshes=("GET /customers/$id",))
@use(require_permission("compliance:write"))
async def screen(id: UUID) -> Screening: ...
```

Most middleware belongs in `_middleware.py` so an entire subtree shares one rule. Use `@use(...)` when a single special action needs a local guard and a subtree file would be heavier than the rule itself.

## Signature

```python
use(*items: Middleware | GuardFn) -> Callable[[Handler], Handler]
```

Every item must be either a `Middleware` instance or a function decorated with `@guard`.

## Graph Metadata

If a guard exposes Causeway metadata, such as `require_permission("x:y")`, the router carries that metadata into the App Graph. `@use(...)` remains execution middleware; the graph is only the inspectable shape.

## See Also

- [Middleware](../../backend/middleware.md)
- [Permissions](../../backend/permissions.md)
- [App Graph](../../client/app-graph.md)
