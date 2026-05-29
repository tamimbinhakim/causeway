# File conventions

Every filename pattern Causeway recognizes inside `src/app/routes/`.

## Quick reference

| Pattern                                | URL effect                              |
| -------------------------------------- | --------------------------------------- |
| [`index.py`](./index-py.md)            | the folder's URL itself                 |
| `foo.py`                               | `/foo`                                  |
| [`$name`](./dollar-name.md)            | dynamic segment → `/{name}`             |
| `$name/...`                            | dynamic folder                          |
| [`(group)/`](./group.md)               | stripped from URL                       |
| [`_middleware.py`](./middleware-py.md) | per-subtree middleware                  |
| [`_scope.py`](./scope-py.md)           | per-subtree DI providers + lifespan     |
| `_*.py`, `_*/`                         | private — colocated helpers, not routed |
| `$$rest.py`, `$$rest/`                 | catch-all — **reserved** for v0.2+      |

Dots in route filenames are rejected. Use folders for URL hierarchy. Route keys use the same tree shape, with `$params` preserved and route groups stripped.

## Translation rules

Implemented in `causeway._paths.url_for`. The full grammar:

1. Walk the path parts from root to leaf.
2. For each folder part:
   - `(group)` → stripped.
   - `$name` → `{name}`.
   - `$$rest` → `NotImplementedError` (reserved).
   - `_*` → never reaches here; private folders are skipped.
   - anything else → literal segment.
3. For the leaf filename (without `.py`):
   - `index` → dropped.
   - `$name` → `{name}`.
   - `$$rest` → `NotImplementedError` (reserved).
   - anything else → literal segment.
4. Join with `/`, prefix with `/`. Empty result → `/`.

## See also

- [Defining routes](../../backend/routing.md)
- [Dynamic segments](../../backend/dynamic-segments.md)
- [Route groups](../../backend/route-groups.md)
