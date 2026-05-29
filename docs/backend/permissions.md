# Permission guards

`require_permission(perm)` is the canonical way to gate routes on a permission string. It's a `@guard`, so it runs before the handler and short-circuits with `401` or `403` as appropriate.

## Usage

```python
# src/app/routes/(admin)/_middleware.py
from causeway import require_permission

middleware = [require_permission("admin:write")]
```

Every route under `(admin)/` now requires the authenticated user to carry `admin:write` (or a permission that implies it).

## The default permission model

Permissions are strings shaped `domain:action`. The framework expands hierarchies:

- `*` is superuser. Any check passes.
- `X:manage` implies `X:write` implies `X:read`.

So a user with `posts:manage` passes a `require_permission("posts:read")` check; a user with `posts:read` does not pass `require_permission("posts:write")`.

```python
from causeway import check_permission, expand_permissions

check_permission({"posts:manage"}, "posts:read")  # True
check_permission({"posts:read"}, "posts:write")   # False
expand_permissions({"posts:manage"})              # {posts:manage, posts:write, posts:read}
```

## Hooking your AuthProvider in

The `AuthProvider` contract grew an `async has_permission(user, perm)` method in `v1.1`. The reference body is `check_permission` against whatever permission set you store on the user:

```python
class MyAuth:
    contract_version = "v1.1"

    async def has_permission(self, user, perm: str) -> bool:
        return check_permission(set(user.permissions), perm)
```

Plugins with a different model (per-resource ACLs, scoped tokens, attribute-based) just return their own answer — `require_permission` only calls `has_permission` and trusts the result.

## Errors

- **Anonymous request** → `401 Unauthorized`.
- **Authenticated but missing the permission** → `403 Forbidden` with `requires <perm>` in the detail.

Both surface via the standard problem+json renderer; no new error type to handle.

## Graph metadata

`require_permission("posts:write")` exposes `posts:write` to the App Graph. That means `causeway inspect --json` and dev tooling can see which route requires which permission without adding a second backend decorator.
