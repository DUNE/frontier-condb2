# Changelog

Human-curated release notes are **optional**. By default every GitHub Release
body is generated from the `#<issue> - <summary>` commit subjects between the
previous release tag and the released revision (see `scripts/release_notes.py`
and `docs/releases.md`).

Use this file only when a release needs prose that the commit log cannot
convey — a milestone, migration steps, or acknowledgements. When a section whose
heading names the exact released version exists here, its content **replaces**
the generated notes for that version verbatim. No CI check requires an entry,
and there is no per-PR obligation to edit this file.

## Format

Add a section keyed to the version (no leading `v`), Keep-a-Changelog style:

```markdown
## [X.Y.Z] - YYYY-MM-DD

Free-form Markdown for the vX.Y.Z release body.
```

The heading `## [X.Y.Z] - ` must match the version being released exactly; the
section runs to the next `## ` heading. Non-matching or malformed headings are
ignored and generation proceeds normally.
