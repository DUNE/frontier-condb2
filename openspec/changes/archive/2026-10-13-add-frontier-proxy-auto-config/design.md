# Design

## Context

See proposal.md - Why. Verified facts about the current stack:

- `ApiClientWrapper._invoke` (`client/pd-cds-api/src/pd_cds_api/wrapper.py:110`) builds `fn-fileget [-r|-R] -c "(serverurl=...)(proxyurl=...)" <query...>`. The connect string is handed verbatim to `frontierConfig_get()` by `fn-fileget` (upstream `client/fn-fileget.c`), so any supported keyword can be injected there.
- Pinned C client (`FRONTIER_REF` 695a979) `frontier_config.c`: `proxyconfigurl` keyword is parsed (l.571); `auto` is rewritten to `http://wpad/wpad.dat` (l.741-742); `http://` and `file://` are the only URL schemes (l.856); the PAC fetch + `FindProxyForURL(serverurl, host)` evaluation runs **during config parsing** (`frontierConfig_doProxyConfig`, l.197) and a failed fetch of all `proxyconfigurl` entries returns `FRONTIER_ECFG` — for `fn-fileget` a fatal exit (code 2), with **no fallback** to `proxyurl`; already-configured `proxyurl` entries are demoted to backup priority when PAC returns proxies (l.1088-1093); `loadbalance=proxies` is ignored with PAC.
- The staged `fn-fileget` binary dlopens `libpacparser.so.1` (shipped beside it in `pd_cds_api_bin`) with `RUNPATH=$ORIGIN`; pacparser availability is already a packaging guarantee, nothing to add.
- Tests fake `subprocess.run` via the `spy` fixture (`client/pd-cds-api/tests/conftest.py`); CI gates: `make lint` (ruff check + format), pyright in `.github/workflows/client.yml:80`, `make coverage` (85% gate over `pd_cds_api`/`pd_cds_cli`).

## Goals / Non-Goals

**Goals:**

- One new configuration value flowing CLI → `ApiClientState` → connect string, with a safe default per issue #50 (`auto`).
- Fail-fast input validation in Python mirroring the C client's accepted grammar.
- Escape hatch preserving today's exact behavior for WPAD-less networks.

**Non-Goals:**

- No PAC parsing/JavaScript execution in Python (stays a thin wrapper; no new dependencies such as `pacparser` bindings).
- No multi-value `proxyconfigurl` lists, no use of the native `FRONTIER_PROXYCONFIGS` env var, no `backupproxyurl` surfacing — single value keeps parity with existing single-value options; the native env var remains available to advanced users untouched.
- No change to perf harness, infra, or packaging.

## Decisions

1. **Field type `str` + validator, not `HttpUrl`/`Literal`.** `pydantic.HttpUrl` cannot express `auto`/`none`; a `Literal["auto","none"] | HttpUrl` union would accept `https://`, which the C client rejects. A `field_validator` enforces exactly: `auto`, `none`, `http://…`, `file://…` (case-sensitive lowercase, matching C `strcmp`s), with an error message listing accepted forms. Alternatives considered: `AnyUrl` subclass with scheme whitelist (heavier, normalizes/reformats the URL we paste into the connect string) — rejected.
2. **Disable sentinel `none`.** Chosen over empty string (the C client silently ignores empty `proxyconfigurl=`, which hides typos and is less visible in `--verbose` output) and over `None` default (would make the CLI env-var pattern diverge from `--cache-proxy-url`, which uses `str | None` only to detect "not provided"). `"none"` never reaches the connect string; `_invoke` conditionally appends `(proxyconfigurl=<value>)`.
3. **Always keep emitting `proxyurl`.** With PAC active the C client demotes it to backup automatically (frontier_config.c:1088), which is exactly the documented-recommended posture and preserves the disable-path byte-for-byte. The upstream hint to use `backupproxyurl` instead applies only to clients older than 2.8.20; the pinned ref is newer.
4. **Token order fixed as `(serverurl=…)(proxyconfigurl=…)(proxyurl=…)`.** The parser is order-insensitive, but a deterministic string keeps connect-string assertions (existing style in `test_wrapper.py`/`test_cli.py`) simple.
5. **CLI: global option `--proxy-config-url`, env `FRONTIER_PROXY_CONFIG_URL`.** Mirrors the existing `--cache-proxy-url`/`FRONTIER_CACHE_PROXY_URL` pattern: CLI default `None` (not provided → keep state default `auto`), help text embeds the resolved default. Validation errors surface as a Typer exit code 2 with the pydantic message.

## Risks / Trade-offs

- [Default `auto` breaks users on networks without WPAD (fatal config error where today's `proxyurl` worked)] → Explicit, documented escape hatch (`--proxy-config-url none` or `FRONTIER_PROXY_CONFIG_URL=none`) in `docs/cli.md`; failure message from `fn-fileget` names the proxyconfig URL; `--verbose` shows the resolved option. Accepted deliberately per issue #50 ("default needs to be auto").
- [Each query pays WPAD discovery latency when `wpad` black-holes (default connect timeout 5 s per PAC server inside `fn-fileget`)] → Native timeouts apply; no Python-side change. Users who care set an explicit PAC URL or `none`.
- [PAC fetched over cleartext HTTP → MITM could redirect queries to a rogue proxy] → Inherent to WPAD/PAC and identical for every Frontier client; noted as a caveat in `docs/cli.md`. Not worsened by this change.
- [`file://` PAC failures are immediately fatal in the C client (no fallback list)] → Accepted native behavior; validation only guarantees scheme shape, docs point at the upstream semantics.
- [`"none"` sentinel shadows a hypothetical real host named `none`] → No scheme prefix, so it could never be a valid URL anyway.

## Migration Plan

Additive field with a default; no API removals. Rollback = revert the change (connection strings revert to `serverurl`/`proxyurl` only). Release notes (next VERSION bump) must call out the new default behavior. Local developers behind non-WPAD networks add `--proxy-config-url none` once or set the env var.

## Open Questions

- None blocking. (Whether `pd-cds` should later expose multi-PAC fallback lists is deferred until a real site asks.)
