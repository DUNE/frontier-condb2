# Proposal

## Why

The frontier client native code (`fn-fileget`, `libfrontier_client.so`, headers, sources, and prebuilt objects) is currently a hand-committed static copy under `client/pd-cds-api/src/pd_cds_api/bin/`. It is duplicated in-tree, un-reproducible, never refreshed, and disconnected from CI: the existing `client.yml` builds frontier from an **unpinned** upstream and uploads the whole `client/` tree to a GitHub Release, but that artifact never feeds the Python wheel, which still ships the committed copy. We must remove `bin/` from the repo and instead build the native client from the upstream [`fermitools/frontier`](https://github.com/fermitools/frontier/tree/master/client) in CI, stage only the runtime artifact into the Python API package, and ship installable PyPI wheels that work across architectures with a low glibc floor.

## What Changes

- **BREAKING** Remove `client/pd-cds-api/src/pd_cds_api/bin/` (sources, objects, `.so`, and committed `fn-fileget`) from the repository; only `bin/__init__.py` (the `importlib.resources` anchor) stays tracked.
- Build a **self-contained static `fn-fileget`** (Model B) from pinned upstream frontier sources in CI — no bundled `libfrontier_client.so`, no `LD_LIBRARY_PATH`, no staged headers. **pacparser support remains enabled** (required).
- Lower the **glibc floor** by building in a **manylinux** image instead of AlmaLinux 9, and provide **multi-arch** wheels via a build matrix (`x86_64`, `aarch64`); AlmaLinux 9+ stays the primary tested target.
- **Reproducible + dynamic CI/CD**: split into a frontier-native-build job and a Python wheel-build job; pin upstream by commit SHA via a repo variable; emit a provenance manifest (resolved SHA, frontier version, arch, glibc floor).
- Publish **per-platform PyPI wheels** (correct platform tags) plus sdist for `pd-cds-api` and `pd-cds-cli`; keep GitHub Release as the artifact home for the native bundle.
- **Local dev parity**: update `uv`/build config so a developer can stage the native binary and build/install/test the packages locally, and so `uv_build` includes the staged binary in the wheel despite it being gitignored.

## Capabilities

### New Capabilities
- `frontier-client-packaging`: How the native frontier client (`fn-fileget`) is built from upstream, staged into the Python API package, packaged as platform-correct PyPI wheels, resolved at runtime, and reproduced locally — including provenance, arch/glibc targeting, licensing, and CI/CD responsibilities.

### Modified Capabilities
<!-- none: no existing specs in this project -->

## Impact

- **Removed**: `client/pd-cds-api/src/pd_cds_api/bin/` native sources/objects/`fn-fileget`/`.so` (all but `__init__.py`).
- **Workflows**: rewrite `.github/workflows/client.yml`; new `.github/workflows/frontier-build.yml`; extend `.github/workflows/release.yml` (matrix + PyPI publish).
- **Packaging**: new `client/pd-cds-api-bin` distribution (setuptools, platform-tagged wheels); `client/pd-cds-api/pyproject.toml` and `client/pd-cds-cli/pyproject.toml` (dependency, artifacts, console-script relocation); root workspace + `uv` build/dev workflow + `Makefile`; a `scripts/` build + staging helper pair.
- **Runtime code**: `pd_cds_api/state.py` (anchor moved to the bin package; `ld_library_path` removed as a no-op for the static binary), `wrapper.py` (no env injection), plus `.gitignore`.
- **Dependencies/tooling**: manylinux image, cross-arch build (native x86_64 + ARM GitHub runners), `uv`, PyPI publish via twine + API-token secrets (org policy: official `actions/*` only), a `FRONTIER_REF` repo variable.
