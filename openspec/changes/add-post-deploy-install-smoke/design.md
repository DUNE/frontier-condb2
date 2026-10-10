# Design

## Context

See proposal.md - Why. Facts this builds on: `pages.yml` (adopt-python-docs-tooling D3) is the sole Pages deployer with jobs `build` (PR gate) and `deploy`; the deploy step exports `steps.deployment.outputs.page_url`; live installability was proven manually during #31 (pip/uv-tool/uv-project channels, aarch64 cross-selection via `pip download --platform`, pip's fragment enforcement under default installs). `client.yml` already gates per-arch wheel contents, glibc tags, and native execution at build time. Constraint: official `actions/*` only.

## Goals / Non-Goals

**Goals:**
- Detect out-of-repo regressions (Pages serving, asset retention, generator-vs-API drift) with near-zero maintenance.
- Keep publication non-transactional-safe: monitoring strictly after deploy.

**Non-Goals:**
- Re-testing installer hash enforcement, native aarch64 execution, generator determinism (see proposal for why each is already covered); alerting beyond a red workflow check; rollback automation.

## Decisions

### D1 — Smoke as third job in `pages.yml`, `needs: deploy`
Placing it beside the deployer keeps the "one workflow owns Pages" invariant reviewable in one file, and `needs: deploy` gives both ordering and the trigger filter for free. Job condition: run only on the release/scheduled surface — `github.event_name == 'workflow_run' || github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'` (not on every docs `push:main`, which adds nothing the weekly doesn't cover and would re-download ~100 MB of deps per prose commit). A separate workflow file was rejected: it would need to re-derive "did the deploy just succeed" via `workflow_run` chaining for no benefit.

### D2 — Weekly `schedule:` on `pages.yml` re-runs the *whole* pipeline
Adding `schedule: - cron: '30 6 * * 1'` (Monday ~06:30Z) makes pages.yml redeploy (docs build + stateless `--from-releases` index rebuild) and then smoke. Choosing full-redeploy-over-smoke-only: the rebuild is itself the self-heal (a vanished release asset drops out of the index automatically; API-shape drift gets caught by the generator's own guards first, at deploy, rather than confusingly at smoke), the API cost is the same paginated listing already run per release, and the schedule can't fork Pages content since this remains the only deployer. `workflow_dispatch` remains the manual version of the same path.

### D3 — Smoke content mirrors the proven manual sequence, inline
Steps: `actions/setup-python@v7` (3.14) → `pip install --upgrade pip` → per-name `pip install --no-deps --index-url <pages>/simple/ pd-cds-api pd-cds-api-bin pd-cds-cli` (single index URL is correct here: `--no-deps` means no third-party resolution; this exercises digest validation + GitHub asset fetch for every artifact) → full `pip install --extra-index-url <pages>/simple/ pd-cds-cli` in a fresh venv (PyPI co-resolution, the documented pattern) → `pd-cds --help` → aarch64 probe `pip download --no-deps --only-binary=:all: --platform manylinux_2_28_aarch64 --python-version 314 --implementation cp --abi cp314 --extra-index-url <pages>/simple/ -d tmp pd-cds-api-bin` asserting the downloaded filename. A short retry loop (3 × 15 s) on the first fetch covers Pages propagation lag after a fresh deploy. Kept as ~25 inline YAML/sh lines, not a `scripts/` module: it is workflow glue using stock installers, exactly the kind of thing the repo's stdlib-script bar (tested, reusable logic) says *not* to script — `docs/releases.md`'s manual recipe remains the human-facing copy.
- *Alt:* reuse `uv` (already bootstrapped in deploy) — either installer works; pip chosen for the smoke to independently cover the channel uv-based CI exercises daily (single-tool monoculture avoidance).

### D4 — URL from deploy output, failure semantics = red check
`pages.yml` deploy job exposes `outputs.page_url: ${{ steps.deployment.outputs.page_url }}`; the smoke consumes `needs.deploy.outputs.page_url` (no hardcoded org URL to rot). No `continue-on-error`: a red run is the alert (Actions schedule-failure notifications handle the weekly case); nothing downstream consumes the smoke.

## Risks / Trade-offs

- **Weekly cron silently disabled if Actions scheduling is paused on the repo/org (private-repo inactivity policy)** → schedule run history is visible in the Actions tab; acceptable for a low-stakes watcher.
- **Smoke depends on PyPI availability** → transient PyPI outage = red weekly run that self-clears next Monday; acceptable noise, not treated as flaky-blocked.
- **A deleted release now *drops* from the index on next rebuild rather than 404ing** (D2 self-heal) → the monitoring requirement still earns its keep: it catches *broken-but-published* states (bad digests, wrong-arch listings, Pages regression) and warns when consumers pinned old versions through `uv.lock`.

## Migration Plan

1. Land the job; trigger one `workflow_dispatch` to prove it green against the current release.
2. Next release exercises it automatically; first weekly run confirms scheduling.
3. Rollback = delete the job + schedule lines; nothing else references them.

## Open Questions

- None material. (Cron day/time: Monday 06:30Z — before the FNAL work week, after weekend GitHub maintenance windows; trivially adjustable.)
