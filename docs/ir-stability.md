# Registration stability

Quay registers three kinds of things into Dyadpy's IR: **routes**, **middleware**, and **background tasks**. These registrations are the contract between Quay and any consumer (the generated TS client, the diagnostics page, `quay diff`, snapshot tests, deploy adapters).

This page describes what's frozen and how it evolves.

## What lives in the IR

For each Quay app:

- **Routes** — path + method + handler input/output schemas + declared raises + middleware chain. Inherits from Dyadpy's existing IR.
- **Background tasks** — task id (module path + function name), queue, retry / backoff policy, payload schema. New surface added by Quay.
- **Plugins** — list of registered adapters by contract (`TaskAdapter`, `Storage`, `KV`, `AuthProvider`). Informational; not part of the wire contract.

If `quay.toml` exposes config keys (`[client] expose_settings = [...]`), those keys also land in the IR — secrets are explicitly excluded.

## Stability invariants (post-1.0)

Additive-only:

- New IR fields are always optional. Consumers that don't know about a field ignore it; consumers that do know never see a missing required value.
- New task registrations are non-breaking — they add capabilities to the client surface.

Breaking (require a major bump and a deprecation cycle):

- Removing or renaming an IR field.
- Changing a field's type in a non-widening way.
- Changing the URL pattern of a registered route (e.g. flipping `(group)/` semantics).
- Changing the queue or retry policy default for `@task`.

## Deprecation cycle

A breaking change goes through:

1. **Minor release N**: the new behavior is added behind a flag; the old behavior is the default and emits a `DeprecationWarning`. Changelog calls it out.
2. **Minor release N+1**: the new behavior is the default; the old behavior is still available via the flag and still emits a `DeprecationWarning`.
3. **Major release**: the old behavior is removed.

That's one full minor of warnings before removal. Long enough for downstream users to migrate; short enough to keep moving.

## What `quay diff` checks

`quay diff <baseline> <candidate>` flags:

- Removed routes.
- Renamed route handlers (same path + method, different function identity → likely a refactor, not breaking).
- Changed request / response schemas (narrowed types, removed fields).
- Removed `@raises` types from the union (clients had to handle them, can't anymore).
- Removed tasks.
- Changed task queue / retry policy defaults.

CI runs `quay diff` against `main` on every PR. Breaking changes annotate the PR with GitHub error annotations and require a `feat!:` or `BREAKING CHANGE:` footer to land.

## What's _not_ in the IR

- Source file paths (handlers move; the IR shouldn't break when they do).
- Private modules / helpers.
- Plugin adapter internals (only the contract type is registered, not the implementation).
- Dev-only middleware (request id, error overlay) — those are framework concerns, not part of the app's contract.

## Versioning the IR itself

The IR schema versions independently from Quay. A Quay `1.x` always emits an IR that conforms to its declared IR-schema version. IR schema changes themselves follow the same deprecation cycle.

## Consumers

The IR is consumed by:

- **Dyadpy** — generates the TypeScript client.
- **`/__quay`** — the dev diagnostics page.
- **`quay diff`** — the CI breaking-change checker.
- **`quay-deploy-*`** — deploy adapters that need to know "which routes are streaming", "which tasks are long-running" to set timeouts correctly.
- **Third-party tools** — anything that wants to introspect a Quay app (admin generators, monitoring sidecars, …).

If you're writing a consumer, the IR schema is your contract. The Python `quay.ir` module is **not** the contract — that's an implementation detail and may change.
