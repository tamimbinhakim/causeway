# Releasing Quay

A maintainer-facing checklist. Everything in here must be true before
`quay-v0.1.0` (PyPI) gets published. Run top to bottom, tick boxes as you go.

> Quay is a **monorepo with one publishable package**: `quay` on PyPI.
>
> Tags follow `release-please-config.json`: `<component>-vX.Y.Z`.

---

## 1. Code gates (must all pass locally on `main`)

```bash
# Python
cd packages/quay
uv sync --all-extras --dev
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy src

# Repo-wide
cd ../..
pnpm install --frozen-lockfile
pnpm exec prettier --check "**/*.{md,json,yaml,yml}"
```

- [ ] Python: ruff lint, ruff format, mypy strict, pytest all green
- [ ] Docs: prettier clean
- [ ] Build artifacts inspected (`uv build` wheel + sdist)
- [ ] No `print(...)` debug statements in `packages/*/src`
- [ ] No `# TODO` / `# FIXME` left in publishable code paths

## 2. Package contents

For each publishable package, verify the wheel includes only what should ship.

```bash
cd packages/quay
rm -rf dist
uv build
unzip -l dist/quay-*-py3-none-any.whl
```

- [ ] `quay/py.typed` is present (PEP 561 marker)
- [ ] All public modules included (`__init__`, `routing/*`, `config`,
      `di`, `tasks`, `ai/*`, `plugins`, `observability`, `health`,
      `errors`, `testing`, `cli`)
- [ ] `METADATA` shows correct version, description, classifiers, license, optional extras
- [ ] `entry_points.txt` registers the `quay` CLI script and the
      `quay.plugins` entry-point group

## 3. Versions, changelogs, manifest

- [ ] `.release-please-manifest.json` reflects the version about to ship
- [ ] `release-please-config.json` `extra-files` entry
      (`packages/quay/src/quay/__init__.py` `__version__`) is current
- [ ] `packages/quay/CHANGELOG.md` has a real release section (not
      just `[Unreleased]`)
- [ ] Changelog entries are user-facing (not commit-ese); breaking
      changes called out at the top of the section
- [ ] Root `CHANGELOG.md` links to the per-package changelog

## 4. Docs

- [ ] `README.md` quickstart copy-pastes without edits
- [ ] `docs/getting-started.md` walks end-to-end from clean install
- [ ] `docs/reference.md` matches actual exports (`__all__` in
      `packages/quay/src/quay/__init__.py`)
- [ ] Package README references the right install command
      (`uv add quay`)
- [ ] `ROADMAP.md` reflects what shipped
- [ ] Badge URLs in `README.md` point at the correct workflows / registries
- [ ] No links go to `localhost`, `127.0.0.1`, or local file paths

## 5. CI / GitHub setup

- [ ] `.github/workflows/ci.yml` runs on the release commit and is green
- [ ] `.github/workflows/release.yml` exists and points at `release-please-config.json`
- [ ] `.github/workflows/codeql.yml` green on `main`
- [ ] Branch protection on `main`: require CI + 1 review, no force-push,
      no admin override
- [ ] Dependabot enabled, weekly cadence, security updates auto-merged

## 6. Registry / publish prerequisites

**PyPI**

- [ ] `quay` project name not taken (check pypi.org/project/quay/) — if
      taken, pick a fallback (`quay-py`, `quayfw`) and update everything
      consistently
- [ ] PyPI Trusted Publisher configured for `tamimbinhakim/quay`,
      `release.yml`, environment `pypi`
- [ ] No `PYPI_TOKEN` lying around in old workflows (we use OIDC)
- [ ] GitHub environment `pypi` exists with deployment protection on `main`

**Provenance**

- [ ] PyPI publish step uses `pypa/gh-action-pypi-publish` (which signs)

## 7. Secrets present in the repo (Settings → Secrets and variables → Actions)

- [ ] `CODECOV_TOKEN` — for the codecov upload in `ci.yml` (optional but
      currently referenced)
- [ ] No leftover personal access tokens or stale API keys

## 8. Release notes draft

Drafted in GitHub Releases, **NOT** auto-published yet:

- [ ] One release: `quay-v0.1.0`
- [ ] The release links its CHANGELOG entry and lists the install command
- [ ] Top-level "v0.1.0 — initial release" announcement post drafted
      separately if needed

## 9. Cold-machine smoke test

Run on a fresh checkout / fresh venv. If you can't do this in <10
minutes, the install path is broken.

```bash
mkdir /tmp/quay-smoke && cd /tmp/quay-smoke
uv init && uv add quay
quay new my-app
cd my-app
uv sync
uv run quay dev &
sleep 2
curl -s http://127.0.0.1:8000/healthz
kill %1
```

- [ ] `uv add quay` works
- [ ] `quay new` scaffolds a runnable app
- [ ] `quay dev` boots; `/healthz` returns 200

## 10. Pull the trigger

Once everything above is ticked:

1. Merge any final PRs into `main`. CI green.
2. release-please opens / updates a "release PR" with version bumps +
   CHANGELOG diffs. Review and merge.
3. The merge triggers `release.yml`, which:
   - Creates a GitHub Release for `quay`.
   - Publishes the Python wheel via PyPI Trusted Publishing.
4. Verify install from a fresh machine (re-run §9 against PyPI, not source).
5. Post the announcement.

If anything goes sideways mid-publish:

- **PyPI half-published:** unyanking PyPI is impossible — bump to the
  next patch, fix, republish. Don't try to delete.
- **Wrong tag pushed:** delete locally and on origin
  (`git push --delete origin <tag>`), re-tag, re-push. Only safe
  _before_ the publish workflow finishes.

## 11. Post-release

- [ ] Smoke test from a clean machine passes against published versions
- [ ] `git log --oneline` matches what's in GitHub Releases
- [ ] PyPI page renders the README correctly
- [ ] Open issues triaged: anything tagged `pre-1.0` reviewed for
      v0.2 inclusion
- [ ] `ROADMAP.md` updated to reflect shipped state if anything moved

---

## Standing rules (don't violate at release time)

- **Never** force-push to `main`.
- **Never** publish from a dirty working tree.
- **Never** edit a published `CHANGELOG.md` — append a follow-up entry.
- **Never** skip CI on a release commit. If you have to, fix CI first.
- **Always** verify `git rev-parse HEAD` matches the tag right before
  publish.
