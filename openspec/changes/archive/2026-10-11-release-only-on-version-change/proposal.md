# Proposal

## Why

Merging to `main` unconditionally runs `release.yml`, whose release job creates-or-**clobbers** the GitHub Release for whatever `VERSION` currently holds. Since rebuilt wheels carry new sha256 digests, a plain merge over an existing tag rotates the published digests behind the live `/simple/` index — breaking any consumer who locked v-previous and violating the project's published-version-immutability policy. The only safe current practice is a version bump on *every* merge to main, which has already forced three semantically-identical releases (0.2.1, 0.2.2, 0.2.3 — the latter two for docs/OpenSpec-only changes) and is trivially forgotten, making digest rotation a silent footgun rather than a policy.

## What Changes

- **Push-triggered merges publish only on VERSION change:** the release job's create/upload steps (and the `workflow_run`-triggered Pages index refresh they imply) become conditional on `v<VERSION>` *not already existing* as a release; when it exists, the job reports "skipped — VERSION unchanged" in the run summary and exits green without touching assets.
- **Dispatch remains the explicit repair override:** `workflow_dispatch` keeps create/update/`--clobber` semantics (documented as the deliberate re-publish/repair path, e.g. after incident recovery or an intentional re-sign), optionally gated by a confirm-style input.
- **Process documentation:** `docs/releases.md` release procedure updated — "bump VERSION when and only when the merge should publish a release"; removes the implicit bump tax and the footgun it guards against.
- Out of scope: suppressing the artifact *builds* themselves on VERSION-unchanged pushes (client.yml gates/smokes still earn their keep per merge), PyPI publish semantics (already token-gated and effectively dormant), retro-clobbering anything already published.

## Capabilities

### New Capabilities
- (none — CI/CD process behavior; `skip_specs: true` at planning. If pursued, revisit whether the release-idempotency guarantee belongs as MODIFIED requirements on `frontier-client-packaging`, whose archived disposition currently assumes the create-or-refresh pattern.)

### Modified Capabilities
- (none planned from `openspec/specs/` at capture time.)

## Impact

- `.github/workflows/release.yml` (release-job step conditions + summary output; possibly one dispatch input).
- `docs/releases.md` procedure + rules bullets.
- Interacts with `add-post-deploy-install-smoke`: VERSION-unchanged merges would no longer produce the release→`workflow_run`→index-refresh chain — consistent with its design (index content only changes with releases), worth cross-checking at design time.

Context: raised while landing the version-agnostic docs fix, which is the third consecutive merge forced to mint a no-op release to avoid clobbering live digests. Captured proposal-only for a future session, same pattern as `mirror-base-images-to-ghcr`.
