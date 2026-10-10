# Proposal

## Why

The published `/simple/` index has failure modes that live entirely outside this repo and are invisible to every current gate: GitHub Pages serving regressions, Releases-API shape drift breaking the generator's assumptions, and — the explicit risk in `wheel-distribution-index` — deleted release assets silently rotting index links. Today those only surface when a *user* tries to install. The 4.1–4.3 manual verifications that closed #31 proved the whole chain installable; nothing keeps it proven. One cheap automated smoke after each release-driven deploy, plus a weekly scheduled run, turns that one-time acceptance evidence into continuous evidence at ~1 job/release + 52 jobs/year.

Deliberately **not** automated (decided during #31's verification, recorded here so it isn't relitigated): installer-side enforcement of `#sha256=` fragments (pip/uv contract, our emission side is golden-tested), native aarch64 *execution* (`client.yml` already builds/gates/smoke-tests per-arch on native runners each release), and rerun byte-diffs (determinism is a unit-proven pure-function property).

## What Changes

- New **post-deploy smoke job** in `pages.yml`: after a successful deploy, installs all three distributions from the **live** Pages index (`--no-deps` direct fetch for each, verifying `#sha256=` digests against actual asset bytes during install), then one full-resolution `pip install pd-cds-cli` with dependencies from PyPI and a `pd-cds --help` execution check, plus the zero-execution aarch64 selection probe (`pip download --platform manylinux_2_28_aarch64`).
- New **weekly `schedule:` trigger** on `pages.yml` (a full redeploy — which self-heals index drift — followed by the smoke), so asset deletion or upstream drift is detected within 7 days.
- Smoke failure = red check only; it runs **after** `deploy-pages` and never blocks or rolls back publication (deploy is not transactional).
- `docs/releases.md`: extend "Verifying a published release" with "…and now automatically" pointer.

## Capabilities

### New Capabilities
- (none)

### Modified Capabilities
- `wheel-distribution-index`: one ADDED requirement — continuous installability monitoring of the published index (post-deploy + weekly). *Ordering note:* this capability's base spec is created when `distribute-wheels-via-github-pages` archives; archive that change first so this delta merges onto an existing spec (the delta is written to apply cleanly either way, mirroring the precedent in the wheels proposal).

## Impact

- `.github/workflows/pages.yml` (smoke job + `schedule:` + `page-url` output wiring; official `actions/*` + run-steps only; ~1 extra job per release and per week).
- `docs/releases.md` one-liner. No script changes: the smoke reuses `pip`/`uv` invocations proven in #31's manual verification, kept inline in the workflow (~20 lines) rather than a new `scripts/` module.
