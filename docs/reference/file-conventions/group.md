# `(group)/`

Folder wrapped in parentheses. Stripped from the URL and route key, preserved as scope metadata.

```
src/app/routes/(admin)/stats.py        →    /stats
src/app/routes/(admin)/users.py        →    /users
src/app/routes/(public)/about.py       →    /about
```

## What groups are for

- Scoping middleware to a slice of the tree (`(admin)/_middleware.py`).
- Scoping DI to a slice of the tree (`(admin)/_scope.py`).
- Marking generated metadata with a scope such as `admin`, `org`, or `public`.
- Visual organization — pulling related routes together without changing URLs.

## Route key effect

```
src/app/routes/(admin)/users/$id.py     →    GET /users/$id
```

The App Graph records `scopes: ["admin"]`; the client route key stays product-shaped.

## Conflict

Routes inside a group can still collide with routes outside it. `(admin)/users.py` and `users.py` both resolve to `/users` — boot fails with a clear error.

## Limitations

- Folder-level only; you can't ungroup a single file.
- Nested groups strip from the URL but accumulate in scope metadata: `(a)/(b)/x.py` has `scopes: ["a", "b"]`.

## See also

- [Route groups](../../backend/route-groups.md)
- [Middleware](../../backend/middleware.md)
- [Scopes](../../backend/scopes.md)
