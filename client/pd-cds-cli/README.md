# pd-cds-cli

`pd-cds` — Typer command-line client for the ProtoDUNE conditions database.
Thin layer over [`pd-cds-api`](../pd-cds-api/README.md); the native
`fn-fileget` comes from [`pd-cds-api-bin`](../pd-cds-api-bin/README.md).
Project overview and fresh-clone setup: [root README](../../README.md).

## Install

From a clone of this repo (after `make stage && uv sync` — see root README):

```bash
uv run pd-cds --help          # workspace venv, no install step
```

End users install the published wheel instead (Python ≥3.14, manylinux
`x86_64`/`aarch64`):

```bash
pip install pd-cds-cli        # pulls pd-cds-api + per-arch pd-cds-api-bin
```

## Global options — place them BEFORE the subcommand

| Option | Env var | Default |
|---|---|---|
| `--api-server-url` | `CONDB_API_SERVER_URL` | `http://dunefrontier.fnal.gov:8000/dune_runcon_prod` |
| `--cache-proxy-url` | `FRONTIER_CACHE_PROXY_URL` | `http://localhost:3128` |
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

Output is written to `./pd-cds-data/` (relative to your CWD; gitignored in
this repo): `<folder>-t_<t0>.<fmt>` or `<folder>-t0_<t0>-t1_<t1>.<fmt>`.

## Examples

```bash
# point-in-time query, verbose
uv run pd-cds -v get-data pdunesp.run_conditionstest --t0 25034

# time range
uv run pd-cds get-data pdunesp.run_conditionstest --t0 25100 --t1 25115

# JSON via a test server, bypassing the local cache
uv run pd-cds --api-server-url http://fermicloud725.fnal.gov:8000/dune_runcon_prod \
    get-data pdunesp.run_conditionstest --t0 28650 -f json
```

## Prerequisites & failure modes

- Live queries need FNAL VPN and a reachable cache proxy (`localhost:3128` by
  default — set one up via the [infra runbook](../../infra/README.md#frontier-squid-cache-setup-on-a-local-workstation)).
- `-v get-data` fails with `No such option` **after** the subcommand: globals
  belong before it (`pd-cds -v get-data ...`).
- Network errors from `fn-fileget` are printed with a non-zero exit code.
- Missing staged runtime (dev checkout only) raises `FileNotFoundError` with
  staging instructions → `make stage`.
