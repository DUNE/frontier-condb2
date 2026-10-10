# Design

## Context

See proposal.md - Why (the merge-implies-clobber footgun and the three forced
no-op releases). Implementation facts this builds on, from the current
`release.yml`:

- The release job (lines 112-179) runs on `workflow_dispatch || refs/heads/main`
  and is where clobbering happens: "Create release" does
  `gh release view "$TAG"` → exists ⇒ `gh release upload --clobber` (rotates the
  `.zip` assets); "Attach unpacked wheels and sdists" then
  `gh release upload --clobber` the `*.whl`/`*.tar.gz` (rotates the digests the
  `/simple/` index pins). Tag = `v${{ needs.read-release-version.outputs.release-version }}`.
- `read-release-version` (lines 33-46) is the single place that resolves the
  version (sparse-checkouts `VERSION`, reads it into an output).
- Workflow `permissions: contents: write`, so `gh` can read/write releases with
  the default `GITHUB_TOKEN`.
- `pages.yml` triggers on `workflow_run: workflows: ["Create ProtoDUNE-CDB
  Release"] types: [completed]` (see below).

## Goals / Non-Goals

**Goals:**
- Make a `push` to main publish a GitHub Release **only when `VERSION` names an
  unpublished version**; otherwise leave the already-published assets (and their
  digests) untouched.
- Keep `workflow_dispatch` as the deliberate re-publish / repair path.
- Make the skip visible and green (a run summary notice), not a silent no-op.

**Non-Goals:**
- Suppressing the client/server **artifact builds** on VERSION-unchanged pushes
  (they still earn their keep as a CI gate — proposal).
- Any change to PyPI semantics (dormant, token-gated) or to Pages deployment
  mechanics.
- Spec-level enforcement of release immutability (see D5 - stays process/docs).

## Decisions

### D1 - Gate the publish *steps*, driven by one boolean from `read-release-version`
`read-release-version` gains a probe step (after reading `VERSION`) that, for
`push` events only, runs `gh release view v<VERSION>` and emits job output
`should-publish`:

- `push`: `should-publish = <release does not exist>`
- non-`push` (i.e. `workflow_dispatch`): `should-publish = true` always.

In the `release` job the four `download-artifact` steps + "Create release" +
"Attach unpacked wheels and sdists" get `if: needs.read-release-version.outputs.should-publish == 'true'`,
and one ungated final step writes the "Release skipped - v<VERSION> already
published (VERSION unchanged); dispatch release.yml to force a re-publish"
notice to `$GITHUB_STEP_SUMMARY` when `should-publish == 'false'` and exits 0.

Why step-gate rather than a job-level `if` on `release`: a job-level `if` skips
the whole job, which GitHub renders faintly and which would swallow the required
run-summary notice; step-gating keeps the `release` job visible-green, still
skips the (bulk) artifact downloads, and prints the explanation. *Alt
considered:* a tiny always-on sibling job for the summary - rejected, it
scatters release logic across two jobs.

### D2 - "Published" == "a GitHub Release for the tag exists", checked via `gh release view`
The protected condition is "this version's assets are already published and
referenced by `/simple/`", which is exactly "the Release object exists." Use
`gh release view v<VERSION>` as the existence check (not a VERSION-file diff,
not tag-only). A pre-existing **git tag with no Release** is treated as
unpublished and allowed to publish (nothing is being protected yet); the create
path then makes the Release. *Alt:* compare HEAD `VERSION` to the latest
release's tag - rejected; it mishandles out-of-order/hotfix tags and re-derives
state `gh` already answers directly.

### D3 - Dispatch stays the override; no new confirm input
`workflow_dispatch` keeps create-or-`--clobber` (deliberate re-publish/repair
after incident recovery or an intentional re-sign). The existing
`publish-target` choice input plus the manual nature of dispatch already mark
intent, so the proposal's "optional confirm input" is **declined** - it adds
surface without a real safety gain (dispatch is never automatic).

### D4 - `pages.yml` / post-deploy smoke interaction: none required (verified)
Gating the publish steps does **not** break the `add-post-deploy-install-smoke`
chain. `workflow_run` fires when the *"Create ProtoDUNE-CDB Release" workflow*
completes with conclusion `success`, and **a skipped job/step is not a failure**
- the run still concludes `success`. So a VERSION-unchanged merge still triggers
a `pages.yml` deploy + smoke, which is a correct, idempotent self-heal (index
content is regenerated from releases that didn't change). The smoke's own
`if:` already covers `workflow_run`; no pages.yml edit is needed and adding a
release-internals condition there would only couple the two files. *Alt:*
suppress the pages deploy on no-release runs - rejected; would skip legitimate
docs-only deploys for no benefit.

### D5 - Keep `skip_specs: true`
No observable capability requirement changes. `frontier-client-packaging` has no
create-or-clobber or immutability requirement to MODIFY, so there is nothing to
merge a delta onto. Release-version immutability stays a documented **process**
rule (`docs/releases.md`), consistent with the proposal. Promoting it to a
spec-enforced guarantee is future work, out of scope here.

## Risks / Trade-offs

- **Legit same-day re-publish of the current version now needs an explicit
  dispatch.** → Mitigated: the skip summary prints the exact repair command and
  D3 keeps dispatch as the blessed path; documented in `docs/releases.md`.
- **A partially-published release** (created but wheels-attach step failed)
  would look "published" to the probe, so the next push skips and leaves it
  incomplete. → Acceptable: that failed run is itself **red** (attach step
  failed), so it surfaces immediately; repair = dispatch (clobber completes the
  attachments). Recorded so nobody re-adds push-clobbering.
- **Probe error handling.** A transient `gh`/network error must not be read as
  "release exists" (skip, wrongly) nor "absent" (publish, wrongly clobber). →
  The probe distinguishes "not found" (proceed to publish) from a hard error
  (`set -euo pipefail`; abort the job loudly) rather than swallowing failures.

## Migration Plan

1. Land the `release.yml` probe + step gates and the `docs/releases.md` updates
   in one PR (this change).
2. No data migration; nothing already-published changes. First VERSION-unchanged
   merge after landing shows `release` green with the skip summary.
3. Rollback = revert the PR (job returns to unconditional create-or-clobber).

## Open Questions

- None material. (Whether to *also* stop building server images on
  VERSION-unchanged pushes is a separate efficiency question explicitly left
  out of scope by the proposal.)
