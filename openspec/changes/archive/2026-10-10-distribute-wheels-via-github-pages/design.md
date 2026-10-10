# Design

## Context

See proposal.md for motivation. Pipeline facts this builds on: every release run already produces, as artifacts, unpacked platform wheels + sdists for all three distributions (`pd-cds-wheels-<arch>`), attached-zip GitHub Releases (idempotent create/update since `aa63dbc`), and a twine publish job that self-skips without `PYPI_API_TOKEN`. Constraints: org policy allows only official `actions/*` on `uses:` lines; GitHub offers **one Pages source per repository site**; wheels are ~6–9 MB each (fine for releases, which have no per-file size problem at this scale).

## Goals / Non-Goals

**Goals:**
- PyPI-quality `pip`/`uv`/`pipx` install UX from a URL under our control; works with zero PyPI accounts.
- Zero-manual operation after releases; repairable; idempotent.
- Coexist on GitHub Pages with the docs site (delivered concurrently by `adopt-python-docs-tooling` via the composed `pages.yml`).

**Non-Goals:**
- OCI-registry (GHCR) package distribution; PyPI trusted publishing; index hosting outside GitHub; sdist source-build support on Windows/macOS.

## Decisions

### D1 — Pages source: GitHub Actions with one composed deployer (supersedes branch-partition plan; 2026-10-09)
GitHub allows one source per site, and Actions-mode deploys **replace the entire site per run**. The user enabled Pages with **GitHub Actions** build-and-deploy (2026-10-09), and `adopt-python-docs-tooling` (Zensical) documents Actions as its publishing path — the original plan (branch `gh-pages` + per-feature `git push` to disjoint dirs) is dead as a *source mechanism*. Decision: keep the path partition (`/simple/**` = this change; everything else = docs) but enforce it *inside* one composed deployer: `.github/workflows/pages.yml` (owned by the docs change) builds the docs tree at `/` and then runs this change's generator in stateless `--from-releases` mode into `site/simple/`, uploading one artifact. Clobbering becomes structurally impossible — there is exactly one writer; official-actions-only holds. Release freshness via `workflow_run` on `release.yml` completion (see docs change D3 for triggers/concurrency).
- *Alt (original):* Pages from branch `gh-pages`, each feature `git push`ing disjoint dirs — rejected by the user's Pages-mode choice; Zensical has no `gh-deploy`-style branch publisher either. *Alt:* `gh-pages` branch as private storage, each producer pushes then deploys the whole branch as artifact — hidden state, push/deploy double-race, two publishers of different snapshots; rejected. *Alt:* host the index elsewhere — no other host available.

### D2 — Index generator: stdlib script, API rebuild as production mode, incremental for local dev
`scripts/build_simple_index.py`:
- **Rebuild mode (`--from-releases`) — production path since D1's amendment:** invoked by `pages.yml` on every Pages deploy; enumerates all releases via the GitHub REST API using `GITHUB_TOKEN`, writes the whole tree to `--site-out <dir>` (new flag; default `simple/`). Asset sha256s prefer the releases-API `assets[].digest` field; fall back to downloading assets only when absent. Stateless — no prior tree needed, which is exactly what a whole-site-replace deployer requires.
- **Incremental mode (kept for local/dev use):** inputs = unpacked `wheels/` dir + tag + optional existing tree; merges rather than rewrites. Same-version reruns dedupe by href → idempotency.
- Both modes emit `<out>/index.html` + `<out>/<normalized-name>/index.html`; each artifact link points at `https://github.com/<org>/<repo>/releases/download/<tag>/<file>#sha256=<digest>` (sha256 fragments per PEP 503). Names normalized PEP 503 (`pd-cds-api`, dir form identical).
- Pure stdlib (`hashlib`, `urllib`, `html`); unit-tested with fixture filenames + golden HTML.

### D3 — Install UX must use extra-index, not replacement index
The Pages index hosts only our three projects; dependencies (`typer`, `pydantic`) live on PyPI. Docs and tests must therefore use `pip install --extra-index-url <pages>/simple/ pd-cds-cli` (or uv `[[tool.uv.index]]` + `explicit = true` for `pd-cds-*` packages so PyPI stays primary), and `uv tool install --index <pages>/simple/ --index-url https://pypi.org/simple pd-cds-cli`. A bare `--index-url` would fail dependency resolution — a common footgun; the CLI README gets a prominent note. (Spec scenario updated accordingly.)

### D4 — Release asset attachment piggybacks on the existing `release` job
After the idempotent create/update block: `gh release upload "$TAG" dist-wheels/*.whl dist-wheels/*.tar.gz --clobber`, sourced from an extra *unpacked* download of `pd-cds-wheels-*` (merge-multiple). Cross-arch sdists share filenames with equivalent content — last-wins under `--clobber`, accepted. Direct-URL assets then exist even for consumers who never touch the index.

### D5 — Index deployment rides `pages.yml`; no dedicated release job (supersedes `distribute-python-index`)
Under composed-deploy D1 there is nothing for `release.yml` to publish: every `pages.yml` deploy regenerates `/simple/**` statelessly from releases (D2 rebuild), and `release.yml` already ends by attaching the per-file assets (D4) that the generator enumerates. The original job (gh-pages bootstrap, incremental run, git commit/push) is deleted; freshness edge = `workflow_run` trigger on `release.yml` completion (docs change D3). Repair path = the existing `workflow_dispatch` on `pages.yml` — no separate `rebuild` input needed since rebuild is now the only production mode.

## Risks / Trade-offs

- **Pages deploy permissions untested on this org** (branch-push probe is moot under Actions source) → first `pages.yml` dispatch (docs change, task 4.2) exercises `pages: write` + `deploy-pages`; if blocked, D4 direct-URL assets still deliver Tier 1 standalone.
- **Index links depend on releases never being deleted** → policy note in docs; stateless rebuild mode is the automatic recovery path (every deploy re-derives from releases).
- **pip default-keyring / index precedence surprises** → documented extra-index patterns (D3) and a CI-verified copy-paste doc test (task 4).
- **Concurrent Pages deploys racing (docs push + release completion)** → single `concurrency: pages` group in `pages.yml` serializes; each deploy is a full stateless composition, so the later run always publishes a complete correct site.
- **sdist-only consumers** (audit workflows that prefer sdists) get our platform-agnostic sdists; `pd-cds-api-bin` sdist intentionally fails to rebuild without staging — accepted (wheels are the supported path; documented).

## Migration Plan

1. Prereq: ~~branch `gh-pages`~~ → Pages source = GitHub Actions — done by user 2026-10-09.
2. Merge this change (generator + D4 assets) together with `adopt-python-docs-tooling`; the first `pages.yml` deploy seeds the index from `v0.2.0` forward as part of the composed site.
3. Verify install matrix (task 4), publish docs URLs. Rollback = disable Pages; assets (D4) remain harmless.

## Open Questions

- Should the index also list `pd-cds` (root umbrella) if it ever gets built? Default: no — only the three published names.
- Retention/undelete policy for old versions (index lists what releases keep) — revisit if artifact retention (90d) ever applies to releases (it doesn't; releases are permanent).
