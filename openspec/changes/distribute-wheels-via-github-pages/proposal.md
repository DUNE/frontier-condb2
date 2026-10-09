# Proposal

## Why

Institutional constraints block publishing to pypi.org, so `pip install pd-cds-cli` is not available. GitHub Pages is enableable for this repo and there is no institutional PyPI mirror. A static PEP 503 "simple" index hosted on GitHub Pages gives pip/uv users a PyPI-equivalent install experience (`--index-url` / configured project index) with automatic per-arch wheel selection — leveraging the platform-tagged manylinux wheels already produced by CI — without third-party services or non-official Actions.

## What Changes

- Generate a PEP 503 simple index (`simple/<package>/index.html` with `#sha256=` fragments) covering all published releases of `pd-cds-api`, `pd-cds-api-bin`, `pd-cds-cli`, built by CI from existing release assets.
- Deploy the index to GitHub Pages as part of the release flow (idempotent, full-rebuild capable), at `https://<org>.github.io/<repo>/simple/`.
- Attach **unpacked wheel/sdist files** as individual GitHub Release assets (direct, pin-able URLs; enables install without the index and air-gapped mirroring).
- The existing twine → PyPI publish path remains, but becomes an optional secondary channel: Pages distribution must not depend on PyPI tokens being set.
- Documentation: canonical install instructions for pip, uv (project `[[tool.uv.index]]` / `uv tool install`), and pipx; README release rules updated.
- Prerequisites noted: Pages enabled for the repo (user-owned action, planned alongside the docs-tooling migration); this change ships the index independent of any docs site.

## Capabilities

### New Capabilities
- `wheel-distribution-index`: How built wheels/sdists are made installable via a static Python package index hosted on GitHub Pages, plus direct-URL release assets, including index correctness, update automation, and install-channel documentation.

### Modified Capabilities
- (none — the sibling `frontier-client-packaging` capability is unaffected; its smoke-gated publish behavior continues to hold. Dependency note: that change should be archived first so main specs exist for cross-references; this change is written to apply cleanly either way.)

## Impact

- `.github/workflows/release.yml` (new distribution job; Pages deploy permissions), possibly a small companion workflow for manual re-seed.
- New `scripts/` index generator (stdlib-only, official-actions-only constraint respected: index deploy uses `git push` to a Pages branch or `actions/upload-pages-artifact`+`deploy-pages`).
- `client/pd-cds-cli/README.md`, `client/pd-cds-api/README.md`, root `README.md` install sections.
- Coordination constraint with the future `adopt-python-docs-tooling` change: both want GitHub Pages — see design (single Pages source decision).
