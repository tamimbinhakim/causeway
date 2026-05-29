# Your first route

Five minutes from `causeway new` to a typed handler responding to `curl` — and a typed TypeScript client falling out the other end.

## 1. Write a handler

```python
# src/app/routes/users/$id.py
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

That's the whole handler. There's no `app.add_route(...)`, no `urls.py`. The file router finds `src/app/routes/users/$id.py`, sees the `@get`-decorated function, and registers `GET /users/{id}`.

> **Naming rule.** The handler parameter name must match the `$` segment: `$id.py` requires `id` in the signature. See [Dynamic segments](../backend/dynamic-segments.md).

## 2. Run it

```bash
uv run causeway dev
```

```bash
curl http://127.0.0.1:8000/users/01000000-0000-0000-0000-000000000000
# {"id":"01000000-0000-0000-0000-000000000000","name":"ada"}

curl -i http://127.0.0.1:8000/users/00000000-0000-0000-0000-000000000000
# HTTP/1.1 404 Not Found
# content-type: application/json
# {"ok":false,"error":{"kind":"NotFound","status":404,"code":"not_found","message":"user 00000000-...","detail":{},"request_id":"..."}}
```

Declared `@raises(...)` errors return typed error envelopes on the wire. The route-key client unwraps them into `CausewayError`. Undeclared internal failures fall back to [`application/problem+json`](https://www.rfc-editor.org/rfc/rfc9457) with scrubbed messages. See [Errors](../backend/errors.md).

## 3. See the route table

Open <http://127.0.0.1:8000/__causeway>. You'll see every discovered route, the registered plugins, current config (secrets redacted), and recent traces. This is the fastest way to know what Causeway thinks of your app.

## 4. Use the generated TypeScript client

Generate the client from the same route IR, then import it from your frontend:

```bash
uv run causeway build
```

```ts
import { createClient } from "./generated/client";

const client = createClient({ baseUrl: "http://127.0.0.1:8000" });

const user = await client.query("GET /users/$id", {
  id: "01000000-0000-0000-0000-000000000000",
});

console.log(user.name); // typed as string
```

The route key comes from the file path and method. `src/app/routes/users/$id.py` plus `@get` becomes `"GET /users/$id"`. `@raises(NotFound)` becomes a typed `CausewayError` branch when the server returns that declared error. No OpenAPI middleware, no operation-name guessing, no generator drift.

## 5. Add a sibling handler

```python
# src/app/routes/users/$id.py  (same file)
from causeway import patch


class UserPatch(Struct):
    name: str | None = None


@patch
async def update(id: UUID, data: UserPatch) -> User:
    return User(id=id, name=data.name or "ada")
```

Multiple HTTP methods can share a route file; method conflicts are caught at boot, not at request time.

## What just happened

1. The router walked `src/app/routes/`, translated `users/$id.py` into `/users/{id}` via the [path rules](../reference/file-conventions/index.md).
2. It stamped the `@get` and `@patch` decorators with their HTTP methods, then registered both with `causeway.App`.
3. The runtime walked your handler signatures into the IR — `id: UUID` becomes a typed path parameter, `data: UserPatch` becomes a typed JSON body, `-> User` becomes the response type, `@raises(NotFound)` becomes a discriminated union on the wire.
4. The same IR emits a generated client with route-key calls like `client.query("GET /users/$id", { id })`, typed end-to-end.

## Where to go next

- [Routing](../backend/routing.md) — the full file-based convention.
- [First product slice](./first-slice.md) — a route, mutation, refresh contract, and frontend in one pass.
- [Handlers](../backend/methods.md) — method decorators, params, responses, errors, streaming.
- [Scopes](../backend/scopes.md) — request-scoped DI providers.
- [Middleware](../backend/middleware.md) — per-subtree wrappers.
- [Plugins](../app/plugins.md) — install Dramatiq, S3, JWT, etc.
- [Reference](../reference/index.md) — every primitive on one page.
