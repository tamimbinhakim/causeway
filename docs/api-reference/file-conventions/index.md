# File conventions

Every filename pattern Causeway recognizes inside `src/app/routes/`.

## Quick reference

| Pattern               | Style        | URL effect                                                |
| --------------------- | ------------ | --------------------------------------------------------- |
| [`index.py`](./index-py.md)              | folder      | the folder's URL itself                                   |
| `foo.py`                                 | both        | `/foo`                                                    |
| [`[name].py`](./bracket-name.md)         | folder      | dynamic segment → `/{name}`                               |
| `[name]/...`                             | folder      | dynamic folder                                            |
| [`$name`](./dollar-name.md)              | dot-flat    | dynamic segment → `/{name}`                               |
| `.index`                                 | dot-flat    | trailing `index` is dropped (match parent)                |
| [`(group)/`](./group.md)                 | both        | stripped from URL                                         |
| [`_middleware.py`](./middleware-py.md)   | folder      | per-subtree middleware                                    |
| [`_scope.py`](./scope-py.md)             | folder      | per-subtree DI providers + lifespan                       |
| `_*.py`, `_*/`                           | folder      | private — colocated helpers, not routed                   |
| `[...rest].py`                           | folder      | catch-all — **reserved** for v0.2+                        |
| `$$rest.py`                              | dot-flat    | catch-all — **reserved** for v0.2+                        |

## Style mixing

Folder hierarchy and dotted leaf concatenate freely. `api/v1.$version.posts.py` → `/api/v1/{version}/posts`. `_middleware.py` and `_scope.py` are always folder-scoped.

## Translation rules

Implemented in `causeway._paths.url_for`. The full grammar:

1. Walk the path parts from root to leaf.
2. For each folder part:
   - `(group)` → stripped.
   - `[name]` → `{name}`.
   - `[...rest]` → `NotImplementedError` (reserved).
   - `_*` → never reaches here; private folders are skipped.
   - anything else → literal segment.
3. For the leaf filename (without `.py`), split on `.`:
   - trailing `index` → dropped.
   - `(group)` → stripped.
   - `$name` → `{name}`.
   - `$$rest` → `NotImplementedError` (reserved).
   - `[name]` → `{name}` (folder-style brackets work in leaves too).
   - anything else → literal segment.
4. Join with `/`, prefix with `/`. Empty result → `/`.

## See also

- [Defining routes](../../building/routing/defining-routes.md)
- [Dynamic segments](../../building/routing/dynamic-segments.md)
- [Route groups](../../building/routing/route-groups.md)
