# CLI guide — `pd-cds`

Typer command-line client for the ProtoDUNE conditions database. Thin layer
over the [`pd_cds_api` Python API](reference/pd_cds_api.md); the native
`fn-fileget` comes from the [`pd-cds-api-bin`](installation.md#what-the-native-wheel-ships)
runtime. Install via [Installation](installation.md) — in a workspace clone
substitute `uv run pd-cds` for `pd-cds` in every example.

## Global options — place them BEFORE the subcommand

| Option | Env var | Default |
|---|---|---|
| `--api-server-url` | `CONDB_API_SERVER_URL` | `http://dunefrontier.fnal.gov:8000/dune_runcon_prod` |
| `--cache-proxy-url` | `FRONTIER_CACHE_PROXY_URL` | `http://localhost:3128` |
| `--proxy-config-url` | `FRONTIER_PROXY_CONFIG_URL` | `auto` — Frontier proxy auto-config (PAC) URL (see [Proxy auto-config](#proxy-auto-config)) |
| `--ttl` (1–3) | `FRONTIER_TTL` | `2` — Frontier cache time-to-live: `1`=short (fresh), `2`=default, `3`=forever |
| `-v`, `--verbose` | — | off (rich panel with resolved options + stdout) |

## `get-data`

```
pd-cds [GLOBAL OPTIONS] get-data {folder} --t0 N [--t1 N] [--dt TYPE] [-f csv|json]
```

| Argument/Option | Meaning |
|---|---|
| `folder` (positional, required) | Conditions folder, e.g. `pdunesp.run_conditionstest` |
| `--t0` (required) | Timestamp, or start of interval when `--t1` is given |
| `--t1` | End of the time interval |
| `--dt` | Restrict to a data type (default: all) |
| `--format`, `-f` | `csv` (default) or `json` |

Output is written to `./pd-cds-data/` (relative to your CWD):
`<folder>-t_<t0>.<fmt>` or `<folder>-t0_<t0>-t1_<t1>.<fmt>`.

The Frontier cache time-to-live defaults to level `2` (normal server cache
duration); `--ttl 3` (or `FRONTIER_TTL=3`) asks the cache to keep immutable
historical ranges forever, `--ttl 1` requests a fresh fetch.

## Proxy auto-config

`--proxy-config-url` selects the [Proxy Auto-Config
(PAC)](https://en.wikipedia.org/wiki/Proxy_auto-config) URL handed to the
native `fn-fileget` client (`proxyconfigurl` in its connection string):

- `auto` (default) — discover the PAC file via WPAD (`http://wpad/wpad.dat`).
- An `http://` or `file://` URL — an explicit PAC file, e.g.
  `http://wlcg-wpad.fnal.gov/wpad.dat`.
- `none` — disable proxy auto-config; only `--cache-proxy-url` is used
  (the pre-PAC behaviour).

The PAC file's `FindProxyForURL` result decides the actual proxies, and it
is evaluated per query by the native client: proxies it returns take
priority, and `--cache-proxy-url` drops to backup. Note that if the PAC URL
cannot be fetched, `fn-fileget` fails with a fatal configuration error — it
does **not** silently fall back to `--cache-proxy-url`. On networks without
a WPAD-provided PAC, pass `--proxy-config-url none` (or a concrete PAC
URL). PAC files are typically served over cleartext HTTP, so the proxy
selection inherits the usual WPAD/PAC trust caveats.

```bash
# no WPAD on this network: behave like older releases (proxy only)
pd-cds --proxy-config-url none get-data pdunesp.run_conditionstest --t0 25034

# site-provided PAC file
pd-cds --proxy-config-url http://wlcg-wpad.fnal.gov/wpad.dat \
    get-data pdunesp.run_conditionstest --t0 25034
```

## Examples

```bash
# point-in-time query, verbose
pd-cds -v get-data pdunesp.run_conditionstest --t0 25034

# time range
pd-cds get-data pdunesp.run_conditionstest --t0 25100 --t1 25115

# immutable historical data: ask the cache to keep it forever
pd-cds --ttl 3 get-data pdunesp.run_conditionstest --t0 25034

# JSON via a test server, bypassing the local cache
pd-cds --api-server-url http://fermicloud725.fnal.gov:8000/dune_runcon_prod \
    get-data pdunesp.run_conditionstest --t0 28650 -f json
```

## Prerequisites & failure modes

- Live queries need FNAL VPN and a reachable cache proxy (`localhost:3128` by
  default — set one up via the
  [runbook](infra/runbook.md#frontier-squid-cache-setup-on-a-local-workstation)).
- `-v get-data` fails with `No such option` **after** the subcommand: globals
  belong before it (`pd-cds -v get-data ...`).
- Network errors from `fn-fileget` are printed with a non-zero exit code.
- `failed to read a proxyconfig url` means the PAC file was unreachable (the
  default `auto` tries WPAD); use `--proxy-config-url none` or a real PAC URL
  — see [Proxy auto-config](#proxy-auto-config).
- Missing staged runtime (dev checkout only) raises `FileNotFoundError` with
  staging instructions → `make stage`.

Programmatic use, including batching multiple ranges into one `fn-fileget`
invocation: see the [API reference](reference/pd_cds_api.md)
(`ApiClientWrapper.run_queries`).
