# `(group)/`

Folder (or dot-flat piece) wrapped in parentheses. Stripped from the URL.

```
src/app/routes/(admin)/stats.py        →    /stats
src/app/routes/(admin)/users.py        →    /users
src/app/routes/(public)/about.py       →    /about
src/app/routes/(admin).stats.py        →    /stats
```

## What groups are for

- Scoping middleware to a slice of the tree (`(admin)/_middleware.py`).
- Scoping DI to a slice of the tree (`(admin)/_scope.py`).
- Visual organization — pulling related routes together without changing URLs.

## Conflict

Routes inside a group can still collide with routes outside it. `(admin)/users.py` and `users.py` both resolve to `/users` — boot fails with a clear error.

## Limitations

- Folder-level only; you can't ungroup a single file.
- Nesting (`(a)/(b)/x.py`) is the same as `x.py` — both layers strip.

## See also

- [Route groups](../../building/routing/route-groups.md)
- [Middleware](../../building/routing/middleware.md)
- [Scopes](../../building/routing/scopes.md)
