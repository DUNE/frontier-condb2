# Tasks

## 1. `release.yml` - publish only on an unpublished VERSION (design D1-D3)

- [x] 1.1 In `read-release-version`: add a step after "Read VERSION file" that computes `should_publish` and expose it as job output `should-publish`. Logic: `workflow_dispatch` => `true`; `push` => probe `gh release view "v<VERSION>"` and set `true` when the release is **absent**, `false` when it **exists**. Use `set -euo pipefail`; distinguish "not found" (non-zero exit whose stderr signals a missing release) from a hard/API error (abort the job loudly - never guess a direction, per D1 risk). Emit only `true`/`false`.
- [x] 1.2 In the `release` job, gate the four `download-artifact` steps + "Create release" + "Attach unpacked wheels and sdists" behind `if: needs.read-release-version.outputs.should-publish == 'true'` (step-gate, not job-gate, so the job stays visible-green and the downloads are skipped on the no-op path).
- [x] 1.3 Add one ungated final step to the `release` job: when `should-publish == 'false'`, append a "Release skipped - v<VERSION> already published (VERSION unchanged); dispatch release.yml to force a re-publish/repair" notice to `$GITHUB_STEP_SUMMARY` and exit 0; no-op when publishing.
- [x] 1.4 Confirm the existing `gh release view`/create-or-`--clobber` branch in "Create release" is retained **unchanged** as the explicit `workflow_dispatch` repair path (dispatch always reaches it via `should-publish == 'true'`); leave `publish-target` / PyPI gating and the client/server build jobs untouched.

## 2. `docs/releases.md` - process documentation (design proposal "What Changes")

- [x] 2.1 Update the "Release procedure" bash block's closing comment: merges to main publish **only when `VERSION` changed**; drop the "every merge cuts GitHub Release vX.Y.Z" wording and state "bump VERSION when and only when the merge should publish a release".
- [x] 2.2 Add a "Rules for new collaborators" bullet codifying the new behavior: push-to-main never rotates an existing version's digests (published-version immutability now enforced by CI, not convention); the deliberate re-publish/repair path is `workflow_dispatch` to `release.yml`; cross-link the existing "Do not delete releases" rule. No hardcoded version numbers (docs style rule).

## 3. Verification

- [x] 3.1 `actionlint` clean on `release.yml`; every `uses:` still official `actions/*`; confirm no Pages deployer/uploader was added or touched (change is confined to `release.yml` + `docs/releases.md`). → actionlint 1.7.7 exit 0; `uses:` = `actions/checkout@v7` / `actions/setup-python@v7` / `actions/download-artifact@v8` + local reusable `client.yml`/`server.yml` only; `grep deploy-pages|upload-pages|configure-pages` = none.
- [x] 3.2 `make docs` strict-green after the 2.1/2.2 edits; run `make lint` + `make test-scripts` (should be unaffected - no `scripts/` change) to confirm the tree stays clean. → `make docs` "No issues found"; `make lint` all passed; `make test-scripts` 16 passed.
- [x] 3.3 Dry-run the truth table and record it in this file: push x {release absent => create; release exists => skip+summary}, dispatch => always create-or-clobber; and assert design D4 - a VERSION-unchanged merge still lets `release.yml` conclude `success`, so `pages.yml`'s `workflow_run` deploy+smoke still fires (skipped steps are not a failed run). → See "Truth table / cross-check" below.
- [x] 3.4 `openspec validate release-only-on-version-change --strict` green (`skip_specs` honored - zero deltas). → valid; `skip_specs` INFO, zero deltas.
- [ ] 3.5 (CI/ops, post-merge) Observe on the next no-bump merge to main: `release` job green with the skip summary and **no** asset change on the latest tag; and on the next version-bump release: the GitHub Release is cut normally. Record links here.

## Truth table / cross-check (3.3)

`should-publish` (from `read-release-version`) drives the `release` job:

| trigger event | `v<VERSION>` exists? | `should-publish` | `release` job outcome | assets touched? |
|---|---|---|---|---|
| `push: main` | no (version was bumped) | `true` | downloads → "Create release" (else-branch: `gh release create`) → "Attach" run | yes — new Release cut (only a genuinely new version) |
| `push: main` | yes (VERSION unchanged) | `false` | all six publish steps skipped; only "Publish-gate skip summary" runs; job **green** | **no** — digests preserved (the footgun this change removes) |
| `workflow_dispatch` | either | `true` (forced) | reaches the pre-existing create-or-`--clobber` branch unchanged | yes — deliberate re-publish/repair (D3 override) |

Probe error handling: only a "not found"-class `gh` failure is read as
"unpublished → `true`"; any other non-zero exit aborts the job (D1 risk), so a
transient API error can neither silently skip a needed publish nor clobber a
published version.

**D4 cross-check (post-deploy smoke chain):** on the VERSION-unchanged push, only
*steps* are skipped — a skipped step is not a failure, the `release` job and the
whole `release.yml` run still conclude `success`. `pages.yml`'s
`workflow_run: ["Create ProtoDUNE-CDB Release"] types:[completed]` therefore
still fires its deploy + `smoke` as today; that deploy rebuilds `/simple/`
statelessly from the (unchanged) releases → an idempotent self-heal with **no**
digest rotation, and the smoke re-proves the current release. So this change does
not weaken the `add-post-deploy-install-smoke` guarantee — the continuous-monitor
chain is preserved, merely exercising a content-identical deploy on no-bump
merges.
