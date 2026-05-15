# Changelog

All notable changes to this project will be documented in this file. The
per-package changelog lives alongside the package and is managed automatically
by [release-please](https://github.com/googleapis/release-please) from
Conventional Commits.

- [`packages/causeway/CHANGELOG.md`](./packages/causeway/CHANGELOG.md)

This file is for repo-wide notes: governance changes, license changes,
toolchain migrations, and other things that don't belong to a single package.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial repository scaffold.
- Governance: the v1.0 stability commitments are written down rather
  than just promised. Four documents cover the corners that matter —
  [`docs/semver.md`](./docs/semver.md) (public API + deprecation cycle),
  [`docs/ir-stability.md`](./docs/ir-stability.md) (route / task
  registration invariants surfaced into the IR),
  [`docs/lts.md`](./docs/lts.md) (support windows + EOL), and the
  plugin-contract-is-part-of-the-surface clause spelled out in the
  README.
