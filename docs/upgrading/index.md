# Upgrading

How to upgrade Causeway across versions. Until 1.0, expect minor APIs to shift between alphas — pin exact versions and read the changelog before upgrading.

## Version status

- **0.1.0a** — current alpha. Public surface is what `causeway.__all__` declares. Anything not listed there is internal and may change in any release.
- **0.1.0** — pending. First stable alpha; after this, dropping the prerelease pin is safe.
- **1.0** — when the public surface freezes. After 1.0, [`semver`](../stability/semver.md) governs every change.

## Upgrade guides

- **[Alpha → 0.1.0](./alpha-to-0-1-0.md)** — what to expect when 0.1.0 ships.

## Tools

- **`causeway diff`** — flags breaking changes in your own app's API surface across builds. See [the CLI page](../api-reference/cli/diff.md).
- **`causeway plugins`** — shows whether your installed plugin adapters still target a contract version Causeway supports.

## Deprecation policy

Pre-1.0:
- Minor versions may break the public API.
- Patch versions only fix bugs (no API changes).
- The plugin contract version (`v1.0`) signals what plugins target. Mismatch warns but doesn't fail.

Post-1.0 ([`semver`](../stability/semver.md)):
- Patch + minor never break.
- Major bumps follow a deprecation cycle: one full minor of `DeprecationWarning` before removal.
- The plugin contract is part of the stable surface.

## See also

- [`semver`](../stability/semver.md)
- [IR stability](../stability/ir-stability.md)
- [LTS](../stability/lts.md)
- [`CHANGELOG.md`](../../CHANGELOG.md)
