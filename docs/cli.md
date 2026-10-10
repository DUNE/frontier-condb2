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
- Missing staged runtime (dev checkout only) raises `FileNotFoundError` with
  staging instructions → `make stage`.

Programmatic use, including batching multiple ranges into one `fn-fileget`
invocation: see the [API reference](reference/pd_cds_api.md)
(`ApiClientWrapper.run_queries`).
