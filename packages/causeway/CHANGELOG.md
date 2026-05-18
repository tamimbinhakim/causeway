# Changelog · `causeway`

All notable changes to the `causeway` Python package will be documented in this
file. Managed automatically by [release-please](https://github.com/googleapis/release-please)
from [Conventional Commits](https://www.conventionalcommits.org/).

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.1](https://github.com/tamimbinhakim/causeway/compare/causeway-v0.3.0...causeway-v0.3.1) (2026-05-18)


### Features

* **causeway:** auto-coerce typed task args via annotations ([a3d9bb9](https://github.com/tamimbinhakim/causeway/commit/a3d9bb9f960e5e5997cef990811f698fa4427952))

## [0.3.0](https://github.com/tamimbinhakim/causeway/compare/causeway-v0.2.1...causeway-v0.3.0) (2026-05-17)


### ⚠ BREAKING CHANGES

* drops the 0.1.0a0 pre-release line. The first published versions on PyPI will be 0.1.0.
* the framework is now distributed as `causeway` (and `causeway-<role>-<impl>` for plugins). Every public surface moves:

### Features

* **causeway:** inline test scenarios with snapshot rewriting ([e897442](https://github.com/tamimbinhakim/causeway/commit/e89744226ba6a2bcd72ea4cda1ef6416d795c044))
* **causeway:** v0.2 — pagination, batch, idempotency, permissions, webhooks, binary export ([45852fd](https://github.com/tamimbinhakim/causeway/commit/45852fd2d6f80aa69d99770e4acdec0aeb67bf03))


### Chores

* prep first 0.1.0 release across all 13 packages ([11ef338](https://github.com/tamimbinhakim/causeway/commit/11ef3382a6263cbe541455dd169a28cf162ebb3d))
* rename quay → causeway across the repo ([83f1213](https://github.com/tamimbinhakim/causeway/commit/83f1213a2176e8338305f8b30f43379d6a614238))

## 0.1.0 (2026-05-16)


### ⚠ BREAKING CHANGES

* drops the 0.1.0a0 pre-release line. The first published versions on PyPI will be 0.1.0.
* the framework is now distributed as `causeway` (and `causeway-<role>-<impl>` for plugins). Every public surface moves:

### Chores

* prep first 0.1.0 release across all 13 packages ([11ef338](https://github.com/tamimbinhakim/causeway/commit/11ef3382a6263cbe541455dd169a28cf162ebb3d))
* rename quay → causeway across the repo ([83f1213](https://github.com/tamimbinhakim/causeway/commit/83f1213a2176e8338305f8b30f43379d6a614238))

## [Unreleased]

### Added

- Initial package scaffold: file-based router, typed config / DI,
  middleware + scope composition, background-task contract + reference
  adapter, plugin registry, `causeway` CLI.
