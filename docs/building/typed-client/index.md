# The typed client

Causeway emits a TypeScript client for your frontend on every change. The Python signature is the contract; the client falls out the other end. No OpenAPI generator, no manual sync, no drift.

This page covers what's in the client and how to consume it. The codegen itself lives in [`dyadpy`](https://github.com/tamimbinhakim/dyadpy) — Causeway's contribution is the project layout, the discovery walk, and the manifest.

## How it's generated

`causeway dev` re-emits `client.ts` on every saved file. The pipeline:

1. The file router walks `src/app/routes/` and produces a `Discovered` snapshot.
2. `dyadpy` walks each handler's signature into the IR (intermediate representation).
3. The codegen turns the IR into a single `client.ts`.

The IR carries:

- one entry per route (method, path, params, body, response, declared errors),
- the named types referenced (Pydantic models, `msgspec.Struct`s, dataclasses, Literal unions, generics),
- the manifest's non-secret `expose_settings` fields.

## What the client looks like

For a handler like:

```python
# src/app/routes/users/$id.py
@get
@raises(NotFound)
async def show(id: UUID) -> User: ...
```

The client gets:

```ts
export interface ApiRoutes {
  users: {
    byId(args: { id: string }): Promise<Result<User, NotFound>>;
  };
}

export const api: ApiRoutes;
```

`User` is a TypeScript interface mirroring the Python `User` struct; `NotFound` mirrors the Python error class.

## Consuming results

```ts
import { api } from "./generated/client";

const result = await api.users.byId({ id: "..." });

if (result.ok) {
  console.log(result.data.name); // typed as `string`
} else if (result.error.kind === "NotFound") {
  console.log("missing"); // narrowed to NotFound branch
}
```

The `Result<T, E>` union is exhaustive — TypeScript forces you to handle the error branch declared via `@raises`.

## Streaming

```python
# Python
@get
async def watch(thread_id: str) -> stream[Event]: ...
```

```ts
// TypeScript
const stream = await api.watch.list({ threadId: "..." });
for await (const event of stream) {
  ...
}
```

`stream[T]` becomes `AsyncIterable<T>` with proper narrowing.

## Settings exposed to the client

```toml
# causeway.toml
[client]
expose_settings = ["env", "feature_flags"]
```

```ts
import { config } from "./generated/client";

console.log(config.env); // "prod"
console.log(config.feature_flags); // { new_dashboard: true }
```

Secret fields (`SecretStr`, `SecretBytes`) are filtered before codegen — listing them in `expose_settings` is a no-op.

## Where to put `client.ts`

Pick a path for your frontend monorepo:

```toml
# causeway.toml
[client]
out = "../frontend/src/generated/client.ts"
```

Default: `./client.ts` in the project root. The dev loop overwrites the file on every change; commit it or `.gitignore` it (most teams `.gitignore` it and let CI rebuild on deploy).

## Breaking change detection

Causeway snapshots the IR at build time:

```bash
causeway build                 # writes dist/ir.json + dist/client.ts
git checkout main
causeway build -o dist-main
causeway diff dist-main/ir.json dist/ir.json
```

`causeway diff` (a thin wrapper over `dyadpy diff`) reports:

- routes added / removed / changed,
- response shape changes,
- error contract changes (new branches, removed branches),
- query / body schema changes.

Wire this into CI to catch contract drift before review:

```yaml
- run: causeway build -o dist-pr
- run: causeway build -o dist-main --ref main
- run: causeway diff dist-main/ir.json dist-pr/ir.json --fail-on breaking
```

## Production build

```bash
causeway build
# dist/
#   ir.json
#   client.ts
#   my_app-0.0.1-py3-none-any.whl
```

Ship `client.ts` to your frontend deploy, `*.whl` to your backend runtime.

## Caveats

- The TS client mirrors the IR exactly. If a handler uses a Python type `dyadpy` can't represent (custom classes without serialization hints, `Any`-typed parameters), the codegen falls back to `unknown` on the client side — type safety degrades to runtime checking.
- Generated code shouldn't be hand-edited. If you need to wrap the client (error handling, retries, logging), build a thin layer in your frontend that imports from the generated module.
- Cross-language IR consumption (Swift / Kotlin / Go clients) is a `dyadpy` feature, not Causeway-specific. Check the [`dyadpy` docs](https://github.com/tamimbinhakim/dyadpy) for the language matrix.

## Next

- [Errors](../handlers/errors.md) — how `@raises` flows to the discriminated union.
- [Streaming](../handlers/streaming.md) — `stream[T]` on both ends.
- [Stability — IR](../../stability/ir-stability.md) — what's stable across versions.
- [Reference — `causeway build`](../../api-reference/cli/build.md)
- [Reference — `causeway diff`](../../api-reference/cli/diff.md)
