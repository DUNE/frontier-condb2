# Proposal

## Why

The user stated the current hub-and-spoke README layout is an intentional stopgap ("I will replace the documents with a more robust tool and layout at a later time"). Since then, the codebase gained complete Google-style docstrings + pydantic `Field(description=…)` metadata — exactly the substrate an autodoc pipeline needs. This change captures that migration.

## What Changes

- Adopt MkDocs Material + `mkdocstrings[python]` (root `.gitignore` already excludes `site/`, indicating the intended tool) rendering the client packages' API reference from docstrings.
- Migrate prose: root README → slim landing page; `infra/README.md` runbook, `tests/perf/README.md`, package READMEs → `docs/` pages with stable nav.
- Wire a docs build (and `--strict` draft/dead-link check) into CI; consider publishing via GitHub Pages.
- Fold in the pre-existing image-path debt note (runbook `docs/images/*` links were verified fixed in-repo; keep assets under the docs tree).

## Capabilities

### New Capabilities
- (intended) None behaviorally; docs tooling is process-only — likely `skip_specs: true` even at planning.

### Modified Capabilities
- (none)

## Impact

`docs/` layout (repo root `.gitignore` already anticipates `site/`), root/package READMEs, a new docs workflow, `uv` dev group (mkdocs deps). **Coordination constraint:** GitHub Pages hosts one site per repo; the `distribute-wheels-via-github-pages` change reserves the `/simple/**` path on the shared `gh-pages` branch (design D1 there) — the docs deploy must target other paths on that branch (or its own composed artifact), never replace the site wholesale.
 Source: explicit user intent during the docs restructure.
