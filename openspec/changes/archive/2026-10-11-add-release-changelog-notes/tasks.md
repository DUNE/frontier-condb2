# Tasks

## 1. `scripts/release_notes.py` core

- [x] 1.1 Scaffold stdlib-only script with argparse subcommands `notes` (`--version`, `--ref`, `--repo`, `--out`) and `feed` (`--repo`, `--out`), shared REST helpers using `GITHUB_TOKEN` and the `build_simple_index.py` injectable-`opener` pattern; exit `0` = content, exit `3` = nothing derivable; module + public-function docstrings pass `make lint` (ruff `D`).
- [x] 1.2 Implement prev-tag selection (name-based semver over `^v\d+\.\d+\.\d+$` tags, strictly below the released version; none → exit 3) and paginated `compare/BASE...REF` fetch (page loop until short page; deterministic ordering).
- [x] 1.3 Implement classification/rendering: drop `parents > 1`, group by `^#(\d+)\s*[-–—]\s*(.+)$`, first-sentence/200-char bullet cap, duplicate-subject collapse, sections desc by issue number, "Other changes" bucket last; golden-file unit tests with fixture compare payloads (incl. merge-commit and untagged-subject cases) under `scripts/tests/`.
- [x] 1.4 Implement `CHANGELOG.md` override: `## [X.Y.Z] - ` exact-version heading, section through next `## `, verbatim body; unit tests for hit, miss, and malformed-heading-ignored.
- [x] 1.5 Implement `feed` mode: releases listing → `## vX.Y.Z — title (YYYY-MM-DD)` + stored body + URL, newest first; golden test from a fixture API page.

## 2. `release.yml` integration

- [x] 2.1 Add "Generate release notes" step (checkout already present in the job; run `python3 scripts/release_notes.py notes --version "$VER" --out notes.md`, capture exit 3 as `fallback` step output); swap create branch `--generate-notes` → conditional `--notes-file notes.md` / `--generate-notes`.
- [x] 2.2 Exists branch: add `gh release edit "$RELEASE_TAG" --notes-file notes.md` (skipped on fallback); confirm rerun idempotency semantics unchanged for assets.
- [x] 2.3 `actionlint` clean; every `uses:` still `actions/*`.

## 3. Docs release-history page

- [x] 3.1 Commit placeholder `docs/release-notes.md` (regeneration header comment) + a `zensical.toml` nav entry (final placement in the consolidated "Releases" section — see 3.4); `make docs` strict-passes with the placeholder.
- [x] 3.2 `pages.yml`: add best-effort `release_notes.py feed` step before `zensical build` in both `build` and `deploy` jobs (`|| echo warning`), env `GITHUB_TOKEN` in deploy (already job-scoped — pass explicitly to the step).
- [x] 3.3 Verify offline path locally: run strict build with the feed step skipped (placeholder renders, nav/link checks green) and with the live API (feed mode against `DUNE/frontier-condb2`) — page lists current releases newest-first.
- [x] 3.4 Docs IA: consolidate the "Releases & maintenance" + "Release history" nav items into a single **"Releases"** section with two children; `git mv docs/releases.md → docs/release-procedures.md` retitled "Release Procedures"; repoint every internal link (`docs/index.md` ×2, `docs/release-notes.md`) — strict docs build green, no dead links.
- [x] 3.5 Navigation theme features (`zensical.toml`): enable `navigation.instant.progress` (top reading-progress bar) and `navigation.expand` (all subsections pre-expanded; confirmed wired — non-active nested toggles render `md-toggle--indeterminate`, applied client-side by the bundle); `navigation.path` breadcrumbs were already present (not duplicated). Strict docs build green.

## 4. Documentation & curation surface

- [x] 4.1 Seed root `CHANGELOG.md` with format-contract header only (no content obligations), cross-linked from `docs/release-procedures.md`.
- [x] 4.2 Add "Release notes" subsection to `docs/release-procedures.md`: generated-by-default mechanism, override heading contract, fallback behavior, pointer to the Release history page and to `gh release edit` for after-the-fact touch-ups (spec: "New maintainer finds the mechanism").

## 5. Verification

- [x] 5.1 `make test-scripts` green incl. new goldens; `make lint` green. → 35 scripts tests pass (16 index + 19 release-notes); `make lint` all passed; `ruff format --check` clean on both new files.
- [x] 5.2 Notes-mode dry run against the real repo state (prev tag exists once #31's release lands) producing a body that matches the current main-vs-previous-tag commit set; eyeball grouping and links. → `notes --version 0.2.3 --ref <origin/main>` diffed v0.2.2..HEAD: grouped `#44`/`#41` with working issue links, merge commits dropped, unclassifiable `#31 follow-up …` subjects preserved under "Other changes", 200-char caps applied, compare footer present.
- [x] 5.3 First live release after merge: GitHub Release body = grouped notes (or documented fallback for the first tag); rerun the release job and confirm body refreshes idempotently (deterministic check via `diff` of two consecutive `notes` outputs). → Deterministic sub-check **passed** (two consecutive `notes --version 0.2.3 --ref <main>` runs byte-identical). The **live GitHub Release** observation is **WAIVED** (maintainer decision 2026-10-10): it requires a real version-bump release (dispatching to force it would `--clobber` v0.2.3's digests, which the immutability policy forbids); deferred to the next genuine release.
- [x] 5.4 Pages deploy shows refreshed history page; docs strict gate green on the PR. → PR-side strict docs gate **verified green** (`make docs` "No issues found"; placeholder + link/nav checks pass). The live Pages-history refresh fires automatically via `workflow_run` on the merge deploy (skipped-steps ≠ failure — the chain proven in #41), **no version bump needed**; eyeballing the rendered page on that deploy is a post-merge follow-up.
- [x] 5.5 `openspec validate add-release-changelog-notes` passes. → `--strict` valid.

## Workflow follow-up

- Archived 2026-10-11 with 5.3's live-release observation waived (bundled into the implementation PR). Post-merge follow-ups, non-blocking: eyeball the first real version-bump release carrying generated notes, and the first Pages deploy's refreshed history page.
- Optional backlog item, not blocking: retro-fill pre-existing release bodies via `gh release edit --notes-file` one-offs.
- Drive-by (this PR, unrelated to the feature): fixed `reportOptionalMemberAccess` pyright warnings in `scripts/` — `(__doc__ or "").partition("\n")[0]` in gen_api_reference.py/release_notes.py/build_simple_index.py and `os.environ.get("GITHUB_API_URL") or args.api_base` guards; `scripts/` isn't in the CI pyright gate (client-only), so these were editor-visible only.
