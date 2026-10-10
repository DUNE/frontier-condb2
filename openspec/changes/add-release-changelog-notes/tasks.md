# Tasks

## 1. `scripts/release_notes.py` core

- [ ] 1.1 Scaffold stdlib-only script with argparse subcommands `notes` (`--version`, `--ref`, `--repo`, `--out`) and `feed` (`--repo`, `--out`), shared REST helpers using `GITHUB_TOKEN` and the `build_simple_index.py` injectable-`opener` pattern; exit `0` = content, exit `3` = nothing derivable; module + public-function docstrings pass `make lint` (ruff `D`).
- [ ] 1.2 Implement prev-tag selection (name-based semver over `^v\d+\.\d+\.\d+$` tags, strictly below the released version; none → exit 3) and paginated `compare/BASE...REF` fetch (page loop until short page; deterministic ordering).
- [ ] 1.3 Implement classification/rendering: drop `parents > 1`, group by `^#(\d+)\s*[-–—]\s*(.+)$`, first-sentence/200-char bullet cap, duplicate-subject collapse, sections desc by issue number, "Other changes" bucket last; golden-file unit tests with fixture compare payloads (incl. merge-commit and untagged-subject cases) under `scripts/tests/`.
- [ ] 1.4 Implement `CHANGELOG.md` override: `## [X.Y.Z] - ` exact-version heading, section through next `## `, verbatim body; unit tests for hit, miss, and malformed-heading-ignored.
- [ ] 1.5 Implement `feed` mode: releases listing → `## vX.Y.Z — title (YYYY-MM-DD)` + stored body + URL, newest first; golden test from a fixture API page.

## 2. `release.yml` integration

- [ ] 2.1 Add "Generate release notes" step (checkout already present in the job; run `python3 scripts/release_notes.py notes --version "$VER" --out notes.md`, capture exit 3 as `fallback` step output); swap create branch `--generate-notes` → conditional `--notes-file notes.md` / `--generate-notes`.
- [ ] 2.2 Exists branch: add `gh release edit "$RELEASE_TAG" --notes-file notes.md` (skipped on fallback); confirm rerun idempotency semantics unchanged for assets.
- [ ] 2.3 `actionlint` clean; every `uses:` still `actions/*`.

## 3. Docs release-history page

- [ ] 3.1 Commit placeholder `docs/release-notes.md` (regeneration header comment) + `zensical.toml` nav entry "Release history" after "Releases & maintenance"; `make docs` strict-passes with the placeholder.
- [ ] 3.2 `pages.yml`: add best-effort `release_notes.py feed` step before `zensical build` in both `build` and `deploy` jobs (`|| echo warning`), env `GITHUB_TOKEN` in deploy (already job-scoped — pass explicitly to the step).
- [ ] 3.3 Verify offline path locally: run strict build with the feed step skipped (placeholder renders, nav/link checks green) and with the live API (feed mode against `DUNE/frontier-condb2`) — page lists current releases newest-first.

## 4. Documentation & curation surface

- [ ] 4.1 Seed root `CHANGELOG.md` with format-contract header only (no content obligations), cross-linked from `docs/releases.md`.
- [ ] 4.2 Add "Release notes" subsection to `docs/releases.md`: generated-by-default mechanism, override heading contract, fallback behavior, pointer to the Release history page and to `gh release edit` for after-the-fact touch-ups (spec: "New maintainer finds the mechanism").

## 5. Verification

- [ ] 5.1 `make test-scripts` green incl. new goldens; `make lint` green.
- [ ] 5.2 Notes-mode dry run against the real repo state (prev tag exists once #31's release lands) producing a body that matches the current main-vs-previous-tag commit set; eyeball grouping and links.
- [ ] 5.3 First live release after merge: GitHub Release body = grouped notes (or documented fallback for the first tag); rerun the release job and confirm body refreshes idempotently (deterministic check via `diff` of two consecutive `notes` outputs).
- [ ] 5.4 Pages deploy shows refreshed history page; docs strict gate green on the PR.
- [ ] 5.5 `openspec validate add-release-changelog-notes` passes.

## Workflow follow-up

- Archive after 5.3 evidence lands (needs one real release through the new step).
- Optional backlog item, not blocking: retro-fill pre-existing release bodies via `gh release edit --notes-file` one-offs.
