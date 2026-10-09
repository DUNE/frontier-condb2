# Proposal

## Why

`release.yml` currently uses a **TEMP** `push: branches: ["*"]` trigger to validate the pipeline from the feature branch; it must return to `[main]`. Once it does, quality gates (ruff, format check, pyright) run only post-merge/on-branch-push — PRs get no pre-merge signal. Recommended during the CI quality-gate work: a small pull_request workflow with the runtime-independent checks.

## What Changes

- New `.github/workflows/ci.yml` on `pull_request` (targeting main): `uv sync` → `ruff check` + `ruff format --check` + `pyright client/`. Chosen checks need no staged native runtime (tests stay in the wheels job, post-staging, where they belong).
- Restore `release.yml` push trigger to `branches: [main]` and retire the TEMP comment (coordinate this and that in one change or a chore commit).
- Optionally require `ci.yml` as a branch-protection status check.
- Deferred micro-considerations recorded alongside (evaluate, don't assume): lift pyright to a single shared job if per-arch runtime becomes annoying; ratchet `--cov-fail-under` 85 → 100 once comfortable.

## Capabilities

### New Capabilities
- (intended) None behavioral (CI process only) — likely `skip_specs: true` at planning.

### Modified Capabilities
- (none)

## Impact

`.github/workflows/ci.yml` (new), `release.yml` trigger, repo branch-protection settings. Source: CI quality-gate recommendation ("add ci.yml when triggers go back to main").
