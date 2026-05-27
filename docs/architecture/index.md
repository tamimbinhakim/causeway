# Architecture

Pages in this section explain what Causeway does internally — useful when you're debugging odd behavior, writing a plugin, or contributing to the framework.

- **[Boot pipeline](./boot-pipeline.md)** — what happens between `causeway dev` and your first request.
- **[IR flow](./ir-flow.md)** — how a handler signature becomes a typed TS client.
- **[Hot reload](./hot-reload.md)** — how the dev loop preserves state across reloads.
- **[Runtime substrate](./runtime-substrate.md)** — the typed-RPC engine under the convention layer; when to reach into `causeway._runtime` and how to build your own framework on the same primitives.

For source-code-level orientation, see [`internals/code-map.md`](../internals/code-map.md).
