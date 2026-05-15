# Stability

What Quay promises about itself. Pin exact versions until v0.1 ships; after that, the rules here are the rules.

- **[Versioning](./semver.md)** — what counts as a breaking change, the deprecation cycle, how `feat:` / `fix:` / `feat!:` Conventional Commits map to releases.
- **[IR stability](./ir-stability.md)** — what Quay registers into the IR, how that surface evolves, and which fields are part of the wire contract.
- **[LTS](./lts.md)** — support windows, backport policy, security-fix cadence.

Two principles cover most of the surface:

1. **Patch + minor never break.** If a `1.2.0 → 1.3.0` upgrade breaks your app, that's a bug in Quay, not in your app.
2. **The plugin contract is part of the stable surface.** A plugin that targets Quay `1.x` keeps working through every `1.y` release.

Major bumps follow a deprecation cycle: one full minor of `DeprecationWarning` before removal, and the warning tells you exactly what to migrate to.
