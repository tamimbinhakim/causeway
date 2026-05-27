# Changelog · `causeway-solid`

All notable changes to the `causeway-solid` npm package will be documented in
this file. Managed automatically by
[release-please](https://github.com/googleapis/release-please) from
[Conventional Commits](https://www.conventionalcommits.org/).

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1-alpha.0](https://github.com/tamimbinhakim/causeway/compare/dyadpy-solid-v0.1.0-alpha.0...dyadpy-solid-v0.1.1-alpha.0) (2026-05-26)


### Features

* add smart reload and lazy client chunks ([bc602b6](https://github.com/tamimbinhakim/causeway/commit/bc602b680a9835abf689a883e8a4169d826c6866))

## [Unreleased]

### Added

- Initial scaffold: `createDyadpyResources(api)` factory returning
  `query`, `mutation`, and `subscription` SolidJS resources/signals.
  `Result<T, E>` envelopes from Python `@raises(...)` decorators are
  unwrapped onto `data` / `error` automatically.
