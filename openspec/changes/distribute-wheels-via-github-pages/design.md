# Design

## Context

See proposal.md for motivation. Pipeline facts this builds on: every release run already produces, as artifacts, unpacked platform wheels + sdists for all three distributions (`pd-cds-wheels-<arch>`), attached-zip GitHub Releases (idempotent create/update since `aa63dbc`), and a twine publish job that self-skips without `PYPI_API_TOKEN`. Constraints: org policy allows only official `actions/*` on `uses:` lines; GitHub offers **one Pages source per repository site**; wheels are ~6–9 MB each (fine for releases, which have no per-file size problem at this scale).

## Goals / Non-Goals

**Goals:**
- PyPI-quality `pip`/`uv`/`pipx` install UX from a URL under our control; works with zero PyPI accounts.
- Zero-manual operation after releases; repairable; idempotent.
- Coexist on GitHub Pages with the future docs site.

**Non-Goals:**
- OCI-registry (GHCR) package distribution; PyPI trusted publishing; index hosting outside GitHub; sdist source-build support on Windows/macOS.

## Decisions

### D1 — Pages source: `gh-pages` branch with path partition, not Actions-artifact deploy
GitHub allows one source per site. `actions/upload-pages-artifact`-style deploys **replace the entire site per run** — the future `adopt-python-docs-tooling` change would clobber the index and vice-versa. Decision: enable Pages from branch `gh-pages` (root `/`), and partition paths: this change owns `/simple/**`; docs tooling will later own `/docs/**` or `/`. Each feature contributes git commits to disjoint directories via plain `git push` with the default `GITHUB_TOKEN` (`permissions: contents: write`) — official-actions-only holds (no `peaceiris/actions-gh-pages`; git commands are steps, not actions).
- *Alt:* single composed deploy job shared by both features — couples two lifecycles; rejected. *Alt:* keep Pages for docs only and host the index elsewhere — no other host available.

### D2 — Index generator: stdlib script, incremental by default, API rebuild as repair
`scripts/build_simple_index.py`:
- **Incremental mode (default, runs on release):** inputs = unpacked `wheels/` from the current run + the existing `simple/` tree on `gh-pages`; emits `simple/index.html` + `simple/<normalized-name>/index.html`; each artifact link points at `https://github.com/<org>/<repo>/releases/download/<tag>/<file>#sha256=<digest>` (digests computed from the local files; sha256 fragments per PEP 503). Names normalized PEP 503 (`pd-cds-api`, dir form identical). Same-version reruns dedupe by href → idempotency.
- **Rebuild mode (`--from-releases`):** enumerates all releases via the GitHub REST API using `GITHUB_TOKEN`, rewrites the whole tree — the drift/corruption repair path and the initial seed.
- Pure stdlib (`hashlib`, `urllib`, `html`); unit-tested with fixture filenames + golden HTML.

### D3 — Install UX must use extra-index, not replacement index
The Pages index hosts only our three projects; dependencies (`typer`, `pydantic`) live on PyPI. Docs and tests must therefore use `pip install --extra-index-url <pages>/simple/ pd-cds-cli` (or uv `[[tool.uv.index]]` + `explicit = true` for `pd-cds-*` packages so PyPI stays primary), and `uv tool install --index <pages>/simple/ --index-url https://pypi.org/simple pd-cds-cli`. A bare `--index-url` would fail dependency resolution — a common footgun; the CLI README gets a prominent note. (Spec scenario updated accordingly.)

### D4 — Release asset attachment piggybacks on the existing `release` job
After the idempotent create/update block: `gh release upload "$TAG" dist-wheels/*.whl dist-wheels/*.tar.gz --clobber`, sourced from an extra *unpacked* download of `pd-cds-wheels-*` (merge-multiple). Cross-arch sdists share filenames with equivalent content — last-wins under `--clobber`, accepted. Direct-URL assets then exist even for consumers who never touch the index.

### D5 — New `distribute-python-index` job in `release.yml`
Runs on `push:main` and `workflow_dispatch` (no token dependency — unlike the publish job), `needs: [read-release-version, build-and-upload-client-artifacts]`, `permissions: contents: write`: checkout → unpacked wheel artifacts → fetch-or-create `gh-pages` (orphan branch bootstrap on first run) → run generator incremental → `git commit` (skip-if-no-change) → `git push`. Dispatch input `rebuild=true` runs D2 rebuild mode instead.

## Risks / Trade-offs

- **Org may block Pages or Actions branch pushes to new branches** → Probe first (task 1.2) before building on it; fallback if blocked: commit the index tree under an in-repo `pages/` branch *or* keep direct-URL assets only (D4 still delivers Tier 1).
- **Index links depend on releases never being deleted** → policy note in docs; rebuild mode recovers consistency.
- **pip default-keyring / index precedence surprises** → documented extra-index patterns (D3) and a CI-verified copy-paste doc test (task 4).
- **gh-pages merge conflicts (docs + index jobs)** → disjoint paths make textual conflicts essentially impossible; push retries once on non-fast-forward.
- **sdist-only consumers** (audit workflows that prefer sdists) get our platform-agnostic sdists; `pd-cds-api-bin` sdist intentionally fails to rebuild without staging — accepted (wheels are the supported path; documented).

## Migration Plan

1. Prereq: enable Pages → branch `gh-pages`, `/` (repo Settings) — user action.
2. Merge the change; run `workflow_dispatch` with `rebuild=true` to seed the index from `v0.2.0` forward.
3. Verify install matrix (task 4), publish docs URLs. Rollback = disable Pages; assets (D4) remain harmless.

## Open Questions

- Should the index also list `pd-cds` (root umbrella) if it ever gets built? Default: no — only the three published names.
- Retention/undelete policy for old versions (index lists what releases keep) — revisit if artifact retention (90d) ever applies to releases (it doesn't; releases are permanent).
