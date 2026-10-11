# Spec Delta

## Purpose

Give every GitHub Release a human-readable note body derived from the project's own commit history — without per-PR process overhead — and make release history readable on the project docs site.

## ADDED Requirements

### Requirement: Generated release notes

Each GitHub Release created by the release workflow SHALL carry a Markdown body summarizing the changes since the previous release, derived from the commit history between the previous release tag and the released revision. The summary SHALL group commits by associated issue/PR number, exclude merge commits, and link to the referenced issues.

#### Scenario: Routine release gets readable notes

- **WHEN** a release is cut for a version with at least one prior release tag
- **THEN** the release body lists one section per issue/PR touched, with the commit-subject summaries as bullets and working links to the issues — and no raw comparison-link-only body

#### Scenario: Untagged history still yields notes

- **WHEN** commits reference an issue via the established `#<n> - ` subject prefix but the corresponding PR is not visible in the compare range
- **THEN** those commits are grouped under that issue's section rather than being dropped

#### Scenario: Unclassifiable commits are preserved

- **WHEN** a commit subject matches no issue prefix
- **THEN** it appears in an "Other changes" section instead of being omitted

### Requirement: Curation override

The system SHALL use a `CHANGELOG.md` section whose heading names the exact release version as the release body verbatim when such a section exists, in preference to generated notes. Presence of the file or obligation to edit it in a PR SHALL NOT be required by any CI check.

#### Scenario: Curated section wins

- **WHEN** `CHANGELOG.md` contains a section for the version being released
- **THEN** the GitHub Release body equals that section's content

#### Scenario: No curation is the normal path

- **WHEN** no section matches the version
- **THEN** generation proceeds and nothing in CI fails due to the missing section

### Requirement: Deterministic and re-runnable publication

Release-note generation SHALL be a deterministic function of the repository state at the referenced commits, and re-running the release workflow for an existing tag SHALL refresh the body to that deterministic content without duplicating sections.

#### Scenario: Rerun after a partial failure

- **WHEN** the release job reruns for a tag whose release already exists
- **THEN** the body is updated in place and matches what a first run would have produced

### Requirement: Graceful fallback

When generated notes are impossible — no prior release tag exists, or the API yields no derivable content — the workflow SHALL fall back to GitHub's automatic notes and complete successfully rather than fail the release.

#### Scenario: First release in history

- **WHEN** a release is cut with no earlier tag to compare against
- **THEN** the run stays green with auto-generated notes

### Requirement: Release history on the docs site

The documentation site SHALL publish a release-history page listing each GitHub Release (version, title, date, body) newest first, refreshed from the Releases API at site build time. Local docs builds without network or without the optional refresh SHALL still succeed via a committed placeholder for that page.

#### Scenario: Fresh deploy shows the newest release

- **WHEN** the composed Pages deploy runs after a new release completes
- **THEN** the release-history page includes the new version above older ones, with the same body text GitHub shows

#### Scenario: Offline contributor build

- **WHEN** a contributor runs the strict docs build with no network access
- **THEN** the build succeeds using the committed placeholder page

### Requirement: Documented release procedure

The project documentation SHALL describe where release bodies come from, how to curate one via `CHANGELOG.md`, and where release history is published.

#### Scenario: New maintainer finds the mechanism

- **WHEN** a contributor reads the releases documentation
- **THEN** they learn the generated-by-default behavior, the override file and heading format, and the docs-site page — without reading workflow source
