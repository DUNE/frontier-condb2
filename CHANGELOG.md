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

## [0.3.0] - 2026-10-13

### Proxy Auto-Config (PAC) support (#50)

- New global CLI option `--proxy-config-url` (env `FRONTIER_PROXY_CONFIG_URL`)
  and new `pd_cds_api.ApiClientState` field `proxy_config_url`. The value is
  passed to the native client as the Frontier `proxyconfigurl` connection
  string keyword, so `fn-fileget` fetches a PAC file and lets its
  `FindProxyForURL` function choose the proxy per query. Accepted values:
  `auto`, `none`, or an `http://`/`file://` URL; anything else is rejected
  before the native client runs.
- **Default behavior change:** the default is now `auto`, i.e. PAC discovery
  via WPAD (`http://wpad/wpad.dat`). Proxies returned by the PAC file take
  priority; `--cache-proxy-url` is still sent and drops to backup priority.
- **Migration:** if no PAC is reachable, `fn-fileget` fails with a fatal
  configuration error (there is no silent fallback). On networks without a
  WPAD-served PAC, restore previous behavior with
  `--proxy-config-url none` / `FRONTIER_PROXY_CONFIG_URL=none`, or point the
  option at a site-provided PAC file, e.g.
  `http://wlcg-wpad.fnal.gov/wpad.dat`.
- Details: [CLI guide — Proxy auto-config](https://dune.github.io/frontier-condb2/cli/#proxy-auto-config).

### Also in this release

- Release process: a merge to `main` publishes a GitHub Release only when
  `VERSION` changed, so rebuilt wheels can no longer clobber the digests the
  live `/simple/` index pins (#44).
- Release notes for GitHub Releases are now generated from merged PR commit
  subjects, with a docs Release-history page and DUNE-branded site theming
  (#47).
- The published wheel index is smoke-tested automatically after every release
  deploy and weekly, verifying installability and digest integrity (#41).
