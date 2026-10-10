# Design

## Context

See proposal.md - Why. Pipeline facts this builds on: `release.yml`'s `release` job already creates-or-updates tags idempotently (`gh release upload --clobber` since `aa63dbc`; body currently only set at create-time via `--generate-notes`); `pages.yml` (docs change) is the single composed Pages deployer and already calls `scripts/build_simple_index.py` with `GITHUB_TOKEN` inside the build tree; repo conventions: stdlib-only `scripts/*.py`, ruff `D` docstrings, opener-injected unit tests with goldens under `scripts/tests/`. Commit subjects follow `#<issue> - <prose>` discipline; merge commits appear as `Merge pull request #<n> …`.

## Goals / Non-Goals

**Goals:**
- Release bodies that read like the PR summaries, produced with zero per-PR work.
- Deterministic under rerun; never fail a release because notes couldn't be derived.
- Docs-site release history that stays fresh with each deploy and builds offline.

**Non-Goals:**
- Enforcing `CHANGELOG.md` edits (deliberately optional); editing GitHub's *auto* notes engine; changelog RSS/atom feeds; retro-fitting historical release bodies in CI (manual `gh release edit` suffices if ever wanted).

## Decisions

### D1 — One stdlib script, two output modes: `scripts/release_notes.py`
`notes` mode: `--version X.Y.Z [--ref HEAD] --out FILE [--repo o/r]` → release body for `vX.Y.Z`.
`feed` mode: `--out docs/release-notes.md [--repo o/r]` → docs page.
Shared internals: REST enumeration (token via `GITHUB_TOKEN`, `urllib`, injectable `opener` — exact `build_simple_index.py` pattern), semver ordering, Markdown rendering. Exit codes: `0` content produced; `3` "nothing derivable" (no prior tag / empty diff) — the workflow keys its fallback off this, not stderr scraping. Pure stdlib keeps the official-actions-only + no-new-deps posture; a generator tool (git-cliff et al.) would add supply-chain surface for strictly less control over this repo's subject conventions.

### D2 — Commit classification & rendering (notes mode)
Base tag = highest `v<semver>` tag strictly below the released version from `/repos/.../tags` (name-based semver compare — no commit-date lookups, fully deterministic). Fetch `/repos/.../compare/BASE...REF`; drop merge commits (`len(parents) > 1`) — their `#n` info is already carried by the branch commits they merge. Group the remainder by regex `^#(\d+)\s*[-–—]\s*(.+)$` on the subject; bullet text = captured summary capped at first sentence/200 chars, link = `[#n](issues/n)`. Sections ordered by issue number desc; non-matching subjects land in "Other changes" last. Identical repeated subjects (revert/reapply churn) collapse to one bullet. The compare endpoint caps commits (250/page) — paginate `page=` until short; at this repo's release sizes it's a formality, but the loop is mandatory for determinism.

### D3 — Curation override: `CHANGELOG.md` at repo root
Heading format `## [X.Y.Z] - YYYY-MM-DD` (Keep-a-Changelog style); the section body (up to the next `## `) replaces generated notes verbatim when the version matches exactly. Lookup happens in `notes` mode from the checkout (no API). The file seeds with format documentation only. Explicitly *not* wired into any gate — per the user's expectation, curation will rarely happen; generated notes are the designed default, not a placeholder awaiting prose.

### D4 — `release.yml` wiring (both create and exists branches)
New step before "Create release": run `notes` mode → `notes.md` (env `GITHUB_TOKEN`, `GITHUB_REPOSITORY` implicit). Create branch: `gh release create … --notes-file notes.md` replaces `--generate-notes`; on exit-3 fallback the step sets an output and the branch keeps `--generate-notes`. Exists branch: additionally `gh release edit "$TAG" --notes-file notes.md` so reruns converge the body (idempotent with `--clobber` asset semantics). `workflow_dispatch` re-runs therefore repair stale bodies for the *current* VERSION tag; older tags stay as published unless someone edits them deliberately.

### D5 — Docs feed page: committed placeholder, overwritten at Pages build
`docs/release-notes.md` is committed as a valid placeholder (HTML comment header: regenerated at deploy). `pages.yml` runs `release_notes.py feed --out docs/release-notes.md` **before** `zensical build` in both jobs, best-effort (`|| echo warning`): CI deploys then always publish fresh history (spec scenario), while API hiccups degrade to the last committed text instead of blocking the site; offline contributors build the placeholder as-is and the strict link gate never sees a missing page (nav entry is static in `zensical.toml`). Feed content: per release — `## vX.Y.Z — title (YYYY-MM-DD)` + stored body + release URL; ordered by API `created_at` desc (drafts invisible to the public listing anyway). This trades one slightly-stale-in-git file for zero build-time coupling between docs correctness and GitHub API availability — the alternative (committing refreshed content) would need a drift gate whose "staleness" is external data, which is unfixable by the contributor and wrong as a CI failure.

### D6 — Documentation landing spot
`docs/releases.md` gains a "Release notes" subsection: mechanism summary, `CHANGELOG.md` heading contract, fallback semantics, and pointer to the new [Release history](release-notes.md) page; root `CHANGELOG.md` header documents the format for the rare curator.

## Risks / Trade-offs

- **Long single-line commit subjects → dense bullets** → first-sentence/200-char cap; full prose remains one click away on the commit/PR; curation hatch exists for milestone releases.
- **Compare API pagination/limits on huge ranges** → paginated loop + documented determinism; at worst the first-release fallback fires.
- **Rate-limited anonymous feed builds** (local runs without `GITHUB_TOKEN`) → best-effort semantics already tolerate a stale page; no CI impact since the deploy always has a token.
- **Two sources of truth for a release body** (CHANGELOG vs generated) → precedence is fixed and documented (override wins), and the body on GitHub is always plain Markdown editable afterward via the UI/`gh`, so neither source is a trap.
- **Placeholder in git diverging from published page** → accepted by design (D5); header comment states the file is regenerated.

## Migration Plan

1. Land script + workflow steps + docs page; nothing observable changes until the next release run.
2. Next merge-to-main (or dispatch) release: bodies generated at publish; docs page refreshes on the following deploy.
3. Optional one-off: retro-fill current release bodies via `gh release edit --notes-file` if history on the release page is wanted immediately — not a CI task.

## Open Questions

- Should the docs nav place Release history under Releases & maintenance or top-level? Default: top-level, after "Releases & maintenance"; trivial to move.
