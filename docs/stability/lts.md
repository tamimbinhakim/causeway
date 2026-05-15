# LTS policy

This page describes what "supported" means for a given Causeway release once we hit `1.0`. Pre-1.0 the rule is simpler: only the latest minor is supported.

## Support windows

After 1.0:

| Track         | What gets backported | For how long                            |
| ------------- | -------------------- | --------------------------------------- |
| `main` (next) | Everything           | Always.                                 |
| Latest minor  | Bug fixes + security | Until the next minor ships.             |
| Latest major  | Security fixes       | 12 months from the day `N+1.0.0` ships. |
| Older majors  | None                 | Out of support; upgrade.                |

Translation: when `2.0.0` ships, the latest `1.y` line keeps receiving security fixes for 12 months. After that, `1.x` is end-of-life.

## What counts as a security fix

- A CVE in Causeway itself.
- A CVE in a direct dependency that Causeway can mitigate with a version bump or workaround.
- A defect that allows an attacker to bypass a documented security boundary (auth provider, plugin sandbox).

Not security fixes:

- Bugs in upstream dependencies that are fixed upstream and only require a routine bump (we ship the bump on the latest minor; older minors get security CVEs only).
- Performance regressions.
- Spec-compliance issues that aren't exploitable.

## Backport process

1. Fix lands on `main`.
2. If it qualifies for backport (bug fix to the latest minor, security fix to older majors), it's cherry-picked into the corresponding `release/X.Y` branch.
3. `release-please` cuts a patch release off the branch.
4. The patch release is announced on the Discussions board.

Backports are not automatic; the maintainer triages each. Most bug fixes do not get backported beyond the latest minor.

## What we promise

- **No silent EOL.** When a major is going out of support, a notice lands in the release notes for the final supported patch, and the GitHub README badge updates.
- **Predictable cadence.** Major bumps happen at most once every 12 months under normal circumstances.
- **Migration guides.** Every breaking change has a paragraph in `CHANGELOG.md` with the diff and the rationale. Every major has a dedicated migration page in `docs/migrations/`.

## What we don't promise

- **A specific Python version forever.** Causeway drops support for a Python minor when the upstream support window closes. The current minimum tracks the Python release cadence — see `pyproject.toml`'s `requires-python`.
- **Stability for `causeway._*` private modules.** Anything underscore-prefixed may change in any release.
- **Stability for third-party plugins.** `causeway-*` plugins not maintained from this repo set their own version policy.

## How to know which version you're on

```bash
causeway --version
```

Or programmatically:

```python
import causeway
causeway.__version__
```

The version string is the source of truth. CHANGELOG entries are keyed by it.
