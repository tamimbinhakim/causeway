# IR flow

How a Python handler becomes a typed TypeScript client.

```
@get
async def show(id: UUID) -> User: ...
       │
       │ (file router)
       ▼
DiscoveredRoute(method="GET", path="/users/{id}", handler=show, ...)
       │
       │ (causeway.routing.register → causeway.App.get("/users/{id}")(show))
       ▼
causeway.App registers the route
       │
       │ (causeway._runtime walks the signature)
       ▼
IR entry:
  {
    method: "GET",
    path: "/users/{id}",
    params: { id: { type: "UUID" } },
    response: { ref: "User" },
    errors: [{ ref: "NotFound" }],
  }
       │
       │ (causeway codegen)
       ▼
client/:
  api.users.byId: (args: { id: string }) => Promise<Result<User, NotFound>>
```

## What lives in the IR

- **One entry per route.** Method, path template, params (path + query), body, response type, declared errors.
- **Named type definitions** referenced by routes. `User`, `NotFound`, `UserPatch`, etc.
- **Settings exposed to the client** (from `causeway.toml`'s `expose_settings`).

## What doesn't

- Handler bodies. The IR is a contract surface, not an implementation manifest.
- DI providers. Those resolve at request time inside the server.
- Plugin state, secrets, internal-only types.

## Sources

The IR is built from:

1. **Handler signatures** — annotations on parameters and return type. Walked by `causeway._runtime.runtime.build_plan`.
2. **`@raises(...)`** — declared error branches.
3. **`stream[T]`** — marker for SSE handlers.
4. **`causeway.toml`** — `[client] expose_settings`.

The router doesn't transform types; it discovers and registers. Type-walking is the runtime's job (`causeway._runtime`).

## Snapshotting

```bash
causeway build       # writes dist/ir.json
```

The IR is JSON-serializable. `dist/ir.json` is checked into the artifact store (or used in CI for `causeway diff`).

## Diffing

```bash
causeway diff dist-main/ir.json dist-pr/ir.json
```

Each change is classified per [IR stability](../stability/ir-stability.md):

- **Non-breaking** — added optional fields, added new routes, added new error branches the client can ignore.
- **Breaking** — removed fields, removed routes, changed types, removed error branches the client must handle.

## Why an IR layer at all

So one source of truth feeds many clients. Today: TypeScript (`causeway codegen`), OpenAPI 3.1 (`causeway openapi`), Swift (`causeway swift`), Kotlin (`causeway kotlin`). Tomorrow: Go, gRPC, anything else. Each generator consumes the same IR.

It also makes contract-stability tooling tractable. `causeway diff` walks the IR rather than parsing Python — that's the only way you get fast, reliable breaking-change detection in CI.

## See also

- [Typed client](../building/typed-client/index.md)
- [`build`](../api-reference/cli/build.md)
- [`diff`](../api-reference/cli/diff.md)
- [IR stability](../stability/ir-stability.md)
- [Runtime substrate](./runtime-substrate.md) — the substrate that owns the IR (`causeway._runtime`).
