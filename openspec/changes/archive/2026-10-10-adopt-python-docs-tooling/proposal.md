# Proposal

## Why

The user stated the current hub-and-spoke README layout is an intentional stopgap ("I will replace the documents with a more robust tool and layout at a later time"). Since then, the codebase gained complete Google-style docstrings + pydantic `Field(description=…)` metadata — exactly the substrate an autodoc pipeline needs. The chosen tool is **Zensical** (user decision; supersedes this stub's original MkDocs Material assumption), and Pages is already enabled with **GitHub Actions** build-and-deploy as the publishing source (user action, 2026-10-09).

## What Changes

- Adopt **Zensical**, managed with **uv** as a `docs` dependency group (`zensical` + `mkdocstrings-python`), configured via `zensical.toml`; local workflow via `uv run zensical` and new `make docs` / `make docs-serve` targets.
- API reference generated from docstrings via Zensical's native `mkdocstrings` for `pd_cds_api` and `pd_cds_cli`; pages are emitted by a committed, deterministic generator (`scripts/gen_api_reference.py`, drift-checked in CI) because Zensical 0.0.69's module-level directives (`api-autonav`/`autoapi`) cannot surface pydantic `Field` descriptions — see design Context.
- Migrate prose: root README → slim landing page; `infra/README.md` runbook, `tests/perf/README.md`, package READMEs → `docs/` pages with stable nav. Leaf READMEs become short pointers (repo browsing still works).
- Add a single composed Pages deployer (`.github/workflows/pages.yml`): builds docs at the site root **and** the PEP 503 index at `/simple/**` into one artifact, so docs and the wheel index from `distribute-wheels-via-github-pages` co-deploy without clobbering (Actions-mode `deploy-pages` replaces the whole site per run — one deployer only). This supersedes the `gh-pages`-branch partition in the wheels change's design D1 (updated in lockstep).
- Wire `zensical build --strict` (dead links / warnings) into CI as a PR gate; deploy on `push: main` (docs paths), after release workflow completion, and on manual dispatch.

## Capabilities

### New Capabilities
- `documentation-site`: the externally observable publishing contract this change grew beyond its "process-only" stub assumption — a single composed GitHub Pages publisher for docs + wheel index with enforced path ownership, atomic co-publication, a strict validation gate on merges, and an API reference derived from the packages' own docstrings. (`skip_specs` removed 2026-10-10: the sole-deployer/clobber-freedom contract in design D1/D3/D4 is a behavioral guarantee the `wheel-distribution-index` capability depends on, and archiving this change with no delta would leave it specified nowhere in main specs.)

### Modified Capabilities
- (none — the wheels `wheel-distribution-index` delta is unchanged; it consumes this capability's `/simple/**` publication without restating the deployer contract.)

## Impact

`docs/` layout (root `.gitignore` already excludes `site/`), root/package/infra/perf READMEs, new `zensical.toml` + `pages.yml` workflow, `uv` dev groups (`pyproject.toml`/`uv.lock`), `Makefile` targets. **Coordination constraint:** owns every path of the Pages site **except** `/simple/**`, which stays the wheels index's; index generation continues to be `scripts/build_simple_index.py` (wheels change), now invoked by `pages.yml` in stateless `--from-releases` mode. Depends on wheels-change tasks 2.1–2.3 (generator) landing first.
 Source: explicit user intent during the docs restructure; tool choice + Pages mode per user (issue #31).
