# Your first route

Five minutes from `causeway new` to a typed handler responding to `curl` — and a typed TypeScript client falling out the other end.

## 1. Write a handler

```python
# src/app/routes/users/[id].py
from uuid import UUID
from msgspec import Struct
from causeway import get, raises
from causeway.errors import NotFound


class User(Struct):
    id: UUID
    name: str


@get
@raises(NotFound)
async def show(id: UUID) -> User:
    if id == UUID(int=0):
        raise NotFound(f"user {id}")
    return User(id=id, name="ada")
```

That's the whole handler. There's no `app.add_route(...)`, no `urls.py`. The file router finds `src/app/routes/users/[id].py`, sees the `@get`-decorated function, and registers `GET /users/{id}`.

> **Naming rule.** The handler parameter name must match the bracketed segment: `[id].py` requires `id` in the signature. See [Dynamic segments](../building/routing/dynamic-segments.md).

## 2. Run it

```bash
uv run causeway dev
```

```bash
curl http://127.0.0.1:8000/users/01000000-0000-0000-0000-000000000000
# {"id":"01000000-0000-0000-0000-000000000000","name":"ada"}

curl -i http://127.0.0.1:8000/users/00000000-0000-0000-0000-000000000000
# HTTP/1.1 404 Not Found
# content-type: application/problem+json
# {"type":"about:blank#not_found","title":"not_found","status":404,"detail":"user 00000000-..."}
```

Errors are rendered as [`application/problem+json`](https://www.rfc-editor.org/rfc/rfc9457) automatically. See [Errors](../building/handlers/errors.md).

## 3. See the route table

Open <http://127.0.0.1:8000/__causeway>. You'll see every discovered route, the registered plugins, current config (secrets redacted), and recent traces. This is the fastest way to know what Causeway thinks of your app.

## 4. Use the generated TypeScript client

`causeway dev` re-emits `client.ts` on every change. From a sibling frontend:

```ts
import { client } from "./generated/client";

const result = await client.users.show({ id: "01000000-..." });
if (result.ok) {
  console.log(result.value.name); // typed as string
} else if (result.error.kind === "NotFound") {
  // forced to handle the NotFound branch
}
```

The `Result<User, NotFound>` shape comes from `@raises(NotFound)`. No OpenAPI middleware, no generator drift.

## 5. Add a sibling handler

```python
# src/app/routes/users/[id].py  (same file)
from causeway import patch


class UserPatch(Struct):
    name: str | None = None


@patch
async def update(id: UUID, data: UserPatch) -> User:
    return User(id=id, name=data.name or "ada")
```

Multiple HTTP methods can share a route file; method conflicts are caught at boot, not at request time.

## What just happened

1. The router walked `src/app/routes/`, translated `users/[id].py` into `/users/{id}` via the [path rules](../api-reference/file-conventions/index.md).
2. It stamped the `@get` and `@patch` decorators with their HTTP methods, then registered both with `dyadpy.App`.
3. dyadpy walked your handler signatures into the IR — `id: UUID` becomes a typed path parameter, `data: UserPatch` becomes a typed JSON body, `-> User` becomes the response type, `@raises(NotFound)` becomes a discriminated union on the wire.
4. The codegen emitted `client.ts` with one function per route, typed end-to-end.

## Where to go next

- [Routing](../building/routing/defining-routes.md) — the full file-based convention.
- [Handlers](../building/handlers/methods.md) — method decorators, params, responses, errors, streaming.
- [Scopes](../building/routing/scopes.md) — request-scoped DI providers.
- [Middleware](../building/routing/middleware.md) — per-subtree wrappers.
- [Plugins](../building/plugins/index.md) — install Dramatiq, S3, JWT, etc.
- [Reference](../api-reference/index.md) — every primitive on one page.
