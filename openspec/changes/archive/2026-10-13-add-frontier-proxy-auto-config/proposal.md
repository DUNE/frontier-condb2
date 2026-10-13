# Proposal

## Why

Sites that require an outbound HTTP proxy (FNAL test-beam, WLCG gateways) currently force users to hand-pick a proxy URL and pass it via `--cache-proxy-url`; nothing adapts when the user moves between networks. The pinned Frontier C client already implements Proxy Auto-Config (PAC): a `proxyconfigurl` keyword in the connection string fed to `fn-fileget -c` makes the client fetch a PAC file (a `FindProxyForURL` JavaScript function), run it through the bundled `libpacparser`, and use the returned proxies. The value `auto` expands to `http://wpad/wpad.dat` (WPAD auto-discovery). Our Python layer never emits that keyword, so the capability is unreachable. See issue #50.

## What Changes

- `pd_cds_api.state.ApiClientState`: new field `proxy_config_url: str`, default `"auto"`, validated to one of `auto`, `none` (disable), or an `http://`/`file://` URL (the C client rejects other schemes at channel-creation time, so Python rejects them up front).
- `pd_cds_api.wrapper.ApiClientWrapper`: append `(proxyconfigurl=<value>)` to the `fn-fileget -c` connection string whenever `proxy_config_url != "none"`; `proxyurl` continues to be emitted and is automatically demoted to backup-proxy priority by the C client when a PAC list is present (>= 2.8.20, which the pinned ref satisfies).
- `pd_cds` CLI: new global option `--proxy-config-url` (env var `FRONTIER_PROXY_CONFIG_URL`) that overrides the state field, following the existing option plumbing pattern.
- **Behavior-change note (non-breaking by agreement in issue #50):** with the default `auto`, `fn-fileget` fails with a fatal config error if no WPAD-served PAC is reachable and the user has not overridden the option — the C client has no fallback-to-`proxyurl` path for a failed PAC fetch. Users on WPAD-less networks pass `--proxy-config-url none` (or a concrete PAC URL) to restore today's behavior; the risk is documented in `docs/cli.md`.
- Full pytest coverage (api + cli suites), ruff lint/format, and pyright type checking pass, matching existing gates.

## Capabilities

### New Capabilities
- `frontier-client-proxy-config`: how the Python client and CLI configure proxy selection (PAC auto-config URL, explicit proxy fallback, disable semantics) for native `fn-fileget` invocations.

### Modified Capabilities
- (none — no existing spec covers client runtime connection behavior; `frontier-client-packaging` covers wheel/build concerns only)

## Impact

- `client/pd-cds-api/src/pd_cds_api/state.py`, `client/pd-cds-api/src/pd_cds_api/wrapper.py`
- `client/pd-cds-cli/src/pd_cds_cli/main.py`
- `client/pd-cds-api/tests/test_state.py`, `test_wrapper.py`, `client/pd-cds-cli/tests/test_cli.py`
- `docs/cli.md` (option table + WPAD caveat); `docs/reference/` regenerated via `make docs-gen`
- No new dependencies: the pinned native build already ships `libpacparser.so.1` in `pd_cds_api_bin` and `pacparser-dlopen` loads it at runtime; no CI/build changes.
