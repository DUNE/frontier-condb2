# Releases & maintenance

## Bumping the pinned Frontier client (`FRONTIER_REF`)

The native `fn-fileget` is built from one commit of
[fermitools/frontier], pinned in the tracked `FRONTIER_REF` file at the repo
root. Bumps are ordinary PR changes — `make stage` and CI read the file
automatically (a repo-level `FRONTIER_REF` variable or a workflow-dispatch
input can override it for one-off runs, but the file is the source of truth).

1. Get a **full 40-character commit SHA** (branch names are rejected; CI
   validates the format):
    - Preferred — a tagged frontier client release: open
      <https://github.com/fermitools/frontier/tags>, pick the newest
      client-relevant tag, and copy the commit SHA it points at, e.g.
      `git ls-remote https://github.com/fermitools/frontier refs/tags/<tag>`.
    - Or the current tip of the client code: open
      <https://github.com/fermitools/frontier/commits/master/client> and copy
      the top commit's full SHA.
2. Update and validate locally:
    ```bash
    echo "<full-sha>" > FRONTIER_REF
    make stage && make test
    grep -E 'sha|frontier_version' client/pd-cds-api-bin/src/pd_cds_api_bin/frontier-manifest.json
    ```
3. PR the `FRONTIER_REF` change (the staged binaries themselves are
   gitignored). After merge, confirm the `frontier-runtime_<VERSION>_<arch>`
   artifacts' `frontier-manifest.json` records the new SHA.

[fermitools/frontier]: https://github.com/fermitools/frontier

## Bumping versions / preparing a release

Five files must carry the **same** semver — `VERSION` drives the GitHub tag
(`vX.Y.Z`) and artifact names, the four `pyproject.toml` files drive the
published wheel versions:

```
VERSION
pyproject.toml                         (workspace root)
client/pd-cds-api/pyproject.toml
client/pd-cds-api-bin/pyproject.toml
client/pd-cds-cli/pyproject.toml
```

Release procedure:

```bash
make check-versions                    # guard: everything agrees pre-bump
# edit all five files to the new version (pick the semver level vs the last release)
uv lock                                # records member versions in the lockfile
make check-versions
make test && make build && make smoke
# PR -> merge to main: release.yml runs the full chain and cuts GitHub Release vX.Y.Z
```

## Rules for new collaborators

- CI enforces the lockstep: the wheels job's static-analysis step runs
  `scripts/check-versions.py`, so a drifted release fails before anything is
  built or published.
- PyPI publishing is skipped (not failed) because `PYPI_API_TOKEN` does not
  exist — **by design, not as a bring-up phase**: institutional constraints
  block pypi.org, so the GitHub Pages `/simple/` index is the primary channel.
  Should that stance ever change, adding the `PYPI_API_TOKEN` repo secret
  activates the dormant job unchanged (TestPyPI uses `TESTPYPI_API_TOKEN`).
- If the dormant PyPI job is ever activated: **PyPI versions are immutable**
  (a failed mid-upload publish cannot reuse its version — bump and republish),
  and dry-runs stay free (`workflow_dispatch` → `publish-target: testpypi`
  targets TestPyPI, an independent index, without burning the PyPI number).
- **Do not delete releases.** The Pages `/simple/` index references
  release-download URLs; removing a release breaks installs. Repair drift by
  dispatching `pages.yml` — every deploy regenerates the whole index
  statelessly from the live releases (`scripts/build_simple_index.py
  --from-releases`).
- **Pages path ownership:** `/simple/**` belongs to the wheel index; every
  other path belongs to this docs site. One composed deployer (`pages.yml`)
  is the only writer, so neither can clobber the other.

## Verifying a published release

When `release.yml` completes, the Pages deploy refreshes `/simple/` automatically
(`workflow_run` trigger). Spot-checks need no matching hardware — pip can
evaluate the index as any platform:

**Wheel selection** — prove an aarch64 installer picks the aarch64 build, from
an `x86_64` host (and vice-versa):

```bash
python3.14 -m pip download --no-deps --only-binary=:all: \
  --platform manylinux_2_28_aarch64 --python-version 314 \
  --implementation cp --abi cp314 \
  -d /tmp/check --extra-index-url https://dune.github.io/frontier-condb2/simple/ pd-cds-api-bin
ls /tmp/check    # => pd_cds_api_bin-<VERSION>-py3-none-manylinux_2_28_aarch64.whl
```

Substitute `manylinux_2_28_x86_64` for the other direction; a native
`pip install --extra-index-url … pd-cds-cli` covers the host platform.

**Index content** — `/simple/` must link exactly the three distributions
(`pd-cds-api`, `pd-cds-api-bin`, `pd-cds-cli`); each project page lists every
matching release file with a `#sha256=` fragment, and non-distribution assets
(zip bundles like `quadlet-artifacts-*.zip`) must never appear.

## CI/CD

`frontier-build.yml` builds the static runtime per-arch (native ARM runner) and
uploads `frontier-runtime_<VERSION>_<arch>` artifacts (+ provenance manifest) →
`client.yml` stages them, builds platform-tagged wheels, hard-gates with
`check-wheel-contents`/`auditwheel`, and smoke-installs each arch →
`release.yml` cuts the GitHub Release and attaches each wheel/sdist as an
individual release asset (its optional twine→PyPI job is dormant —
institutionally blocked, see the rules above) → `pages.yml` deploys this site
together with the regenerated `/simple/` package index.

## Docs toolchain maintenance

This site is built with [Zensical](https://zensical.org), pinned via the `docs`
dependency group in `pyproject.toml` / `uv.lock`:

```bash
make docs           # strict build (fails on warnings / dead links) -> site/
make docs-serve     # live preview at http://localhost:8000
```

The docs build never needs the staged native runtime: CI syncs the `docs`
group with `--no-install-package pd-cds-api-bin` (that distribution's
`setup.py` intentionally refuses to build without `fn-fileget` & co., which
is right for wheels but not for docs) and builds via `uv run --no-sync`.
Locally, `make docs` runs inside the full dev venv as usual.

Zensical is pre-0.1: upgrades are deliberate, single-package lock changes,
never floating —

```bash
uv lock --upgrade-package zensical && uv sync --group docs
make docs           # strict build must pass before landing the bump
```

Documentation style rule: never hardcode a release version into `docs/` —
use `<VERSION>` / `vX.Y.Z` placeholders (literal versions go stale with the very
next release; the site prose outlives every tag).

The API reference pages are generated from the client packages' docstrings by
the `api-autonav` + `mkdocstrings` plugins (config in `zensical.toml`) — no
per-module stub files to maintain; if a package fails to import, the docs
build fails loudly (a feature: doc CI doubles as an import smoke test).
