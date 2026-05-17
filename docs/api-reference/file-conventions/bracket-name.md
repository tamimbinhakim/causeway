# `[name].py` and `[name]/`

Folder-style dynamic segment. The bracketed name becomes a path parameter; the handler signature drives parsing.

```
src/app/routes/users/[id].py               →    /users/{id}
src/app/routes/users/[id]/posts.py         →    /users/{id}/posts
src/app/routes/users/[id]/posts/[postId].py →    /users/{id}/posts/{postId}
```

## Rules

- The handler parameter name must match the bracketed name exactly. `[id].py` requires `id` in the signature.
- The annotation drives parsing: `id: UUID` parses to `UUID`; `id: int` parses to `int`; a parse failure returns 400.
- Bracket characters in filenames work because Causeway loads route files via `importlib.util.spec_from_file_location`, not the `import` machinery.

## Binding example

```python
# src/app/routes/users/[id].py
from uuid import UUID
from causeway import get

@get
async def show(id: UUID) -> User: ...
```

## Catch-all (reserved)

`[...rest].py` is reserved for v0.2+. Today it raises `NotImplementedError` at boot.

## See also

- [Dynamic segments](../../building/routing/dynamic-segments.md)
- [`$name`](./dollar-name.md) — dot-flat equivalent.
