# Tasks

## 1. Workflow changes (`.github/workflows/pages.yml`)

- [x] 1.1 Deploy job: add `outputs: page-url: ${{ steps.deployment.outputs.page_url }}`.
- [x] 1.2 Add `schedule:` trigger (`cron: '30 6 * * 1'`) to the workflow's `on:` block; verify the deploy job's existing `if:` already admits `schedule` events (it excludes only `pull_request`/failed `workflow_run` — extend if needed).
- [x] 1.3 Add `smoke` job per design D1/D3: `needs: deploy` (+ job-level condition limiting to `workflow_run` / `schedule` / `workflow_dispatch`), `permissions: contents: read`, steps = setup-python 3.14 → per-name `--no-deps --index-url <page-url>simple/` installs of `pd-cds-api`, `pd-cds-api-bin`, `pd-cds-cli` (with 3×15 s retry priming loop on the first fetch) → fresh-venv full-resolution `pip install --extra-index-url … pd-cds-cli` → `pd-cds --help` → aarch64 `pip download --platform manylinux_2_28_aarch64 … pd-cds-api-bin` asserting the `manylinux_2_28_aarch64` filename in the result.

## 2. Docs

- [x] 2.1 `docs/releases.md` "Verifying a published release": append one sentence — the spot-checks now also run automatically post-release and weekly via the `pages.yml` smoke job (red run = failing check, deploys never blocked).

## 3. Verification

- [x] 3.1 `actionlint` clean on `pages.yml`; `uses:` still official `actions/*` only; strict docs build still green (2.1). → actionlint 1.7.7 exit 0; `uses:` audit = 8× official `actions/*` only (smoke adds just `setup-python@v7`); `make docs` strict = "No issues found".
- [ ] 3.2 First live proof: `workflow_dispatch` pages.yml post-merge → smoke job green end-to-end against the current release; record the run link in this file.
- [ ] 3.3 Negative proof (once, manual): temporarily point the smoke at a bogus index URL (or corrupt a local mirror per the #31 4.3 recipe) on a throwaway branch dispatch and confirm the job fails loudly naming the distribution; do not merge.
- [ ] 3.4 After the first scheduled Monday run and the first release-triggered run: confirm both appear green in Actions history → requirement satisfied continuously.
- [x] 3.5 `openspec validate add-post-deploy-install-smoke` green. → `openspec validate --strict` = valid.

## Workflow follow-up

- Archive order: `distribute-wheels-via-github-pages` first (creates the `wheel-distribution-index` base spec), then this change (its ADDED requirement merges onto it) — mirrors the ordering note in this proposal's Capabilities.
- If the weekly cron ever shows a silent gap (Actions scheduling paused), re-enable or move cadence into a dispatch from an existing workflow — not worth complexity today.
