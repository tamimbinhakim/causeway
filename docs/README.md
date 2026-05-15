# Quay docs

A backend framework for type-safe Python APIs. The folder tree is the route table; the typed TypeScript client falls out the other end for free.

If you're new here, [the story behind why this exists](./why-quay.md) is the warmest place to start.

## Start

- **[Get started](./getting-started.md)** — clone, scaffold, see the route tree and a typed handler in five minutes.
- **[Why Quay](./why-quay.md)** — the AML-software → FastAPI → dyadpy → Quay story, the six principles, the positioning matrix, the explicit non-goals.

## Use

The conceptual docs. Each page covers one primitive end-to-end.

- **[Routing](./routing.md)** — file-based routing, both folder style (`[id].py`) and dot-flat (`users.$id.py`), middleware, scopes, route groups.
- **[Plugins](./plugins.md)** — the plugin contract, entry-point discovery, explicit `register()`, lifecycle, per-env activation.
- **[Tasks](./tasks.md)** — `@task` and `@cron` decorators, the adapter contract, eager mode for tests, swapping reference for production.
- **[Reference](./reference.md)** — every primitive on one page. The thing you keep open in a tab.

## Stability

What Quay promises about itself.

- **[Versioning](./stability/semver.md)** — what counts as a breaking change.
- **[IR stability](./stability/ir-stability.md)** — what flows into the IR, how that surface evolves.
- **[LTS](./stability/lts.md)** — support windows, backport policy.

## Internals

For people working **on** Quay rather than building **with** it.

- **[Architecture](./internals/architecture.md)** — what happens when you type `quay dev`.
- **[Code map](./internals/code-map.md)** — file-by-file tour of `packages/quay/src/quay/`.
- **[Contributing (deep)](./internals/contributing.md)** — coding conventions beyond the top-level CONTRIBUTING.md.
- **[Testing strategy](./internals/testing.md)** — what we test, what we don't.
- **[Releases](./internals/releases.md)** — how release-please drives PyPI publishes.
- **[Writing a new official plugin](./internals/plugin-authoring.md)** — the on-ramp for sibling `quay-<role>-<impl>` packages.

---

Something wrong, confusing, or missing? Open a [doc issue](https://github.com/tamimbinhakim/quay/issues/new?labels=docs). Meta-PRs (improving these very docs) count and are appreciated.
