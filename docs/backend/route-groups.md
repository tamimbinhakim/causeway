# Route groups

Route groups let you organize the tree — by team, feature, or auth level — **without** changing the URL surface.

## The convention

A folder wrapped in parentheses is stripped from the URL:

```
src/app/routes/(admin)/stats.py       →    /stats
src/app/routes/(admin)/users.py       →    /users
src/app/routes/(public)/about.py      →    /about
```

## Why use them

Three things you can do once you have groups:

1. **Scope middleware to a slice of the tree.** A `_middleware.py` inside `(admin)/` only applies to admin routes, even though those routes live at the URL root.
2. **Scope DI to a slice of the tree.** Same for `_scope.py` — providers declared in `(admin)/_scope.py` are only visible to admin handlers.
3. **Attach scope metadata without URL noise.** The group name is stripped from the HTTP path, but preserved in the App Graph as a scope.
4. **Pull two trees apart visually.** Public-facing endpoints in `(public)/`, internal admin endpoints in `(admin)/`, and org-scoped product endpoints in `(org)/` can be separate subtrees without leaking implementation names into URLs.

```
src/app/routes/
├── (public)/
│   ├── index.py              # /
│   └── about.py              # /about
├── (admin)/
│   ├── _middleware.py        # require_admin guard
│   ├── _scope.py             # admin audit logger
│   ├── stats.py              # /stats
│   └── users.py              # /users
└── billing/
    ├── _scope.py             # stripe client
    └── webhooks.py           # /billing/webhooks
```

> **Watch out.** Group folders are stripped from the URL. If you want `/billing/webhooks`, use a real folder (`billing/webhooks.py`), not a group (`(billing)/webhooks.py` becomes `/webhooks`).

## Route keys and scopes

Groups are not part of the route key:

```
src/app/routes/(org)/customers/$id.py
```

becomes:

| Field     | Value                |
| --------- | -------------------- |
| HTTP path | `/customers/{id}`    |
| Route key | `GET /customers/$id` |
| Scopes    | `["org"]`            |

That split is deliberate. URLs and route keys stay product-shaped; scopes carry the organizational meaning for middleware, generated metadata, agents, and dev tooling.

## A worked example: auth tiers

A common pattern is one group per auth tier:

```
src/app/routes/
├── (public)/                 # no auth required
│   ├── login.py
│   └── signup.py
├── (user)/                   # require_login
│   ├── _middleware.py        # auth guard
│   ├── profile.py            # /profile
│   └── settings.py           # /settings
└── (admin)/                  # require_admin
    ├── _middleware.py        # admin guard
    ├── stats.py              # /stats
    └── users.py              # /users
```

Every handler under `(user)/` runs the user-auth guard; every handler under `(admin)/` runs the admin-auth guard. The URL surface stays clean (`/profile`, not `/user/profile`).

## Collision rules

Two routes can't resolve to the same URL — including across groups:

```
src/app/routes/(admin)/users.py       →    /users
src/app/routes/users.py               →    /users      ← conflict at boot
```

The discovery walk raises a `TypeError` listing both source files.

## Limitations

- Groups are folder-level only — there's no way to "ungroup" a single file out of a folder. If you need that, pull the file up a level.
- Nested groups still strip from the URL, but both names appear in scope metadata. `(a)/(b)/x.py` has the same HTTP path as `x.py`, with `scopes: ["a", "b"]`.

## Next

- [Middleware](./middleware.md) — the most common use of route groups.
- [Scopes](./scopes.md)
