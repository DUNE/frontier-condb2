# ProtoDUNE Conditions Data Service (frontier-condb2)

Client, server infrastructure, and perf tests for the ProtoDUNE run-conditions
database, served through the [Frontier](https://frontier.cern.ch) stack and a
ConDB2 REST backend.

> **📖 Documentation lives on the site:**
> <https://dune.github.io/frontier-condb2/> — installation (PEP 503 wheel
> index at [`/simple/`](https://dune.github.io/frontier-condb2/simple/)), CLI
> guide, generated API reference, Locust perf harness, infrastructure runbook,
> and release/maintenance rules. This README is just the repo-browsing map;
> sources for the site are under [`docs/`](docs/).

## Repository map

| Path | What it is | Docs (site) |
|---|---|---|
| `client/pd-cds-api/` | Python API wrapping `fn-fileget` (RunConditions/ApiClientState/ApiClientWrapper) | [API reference](https://dune.github.io/frontier-condb2/reference/pd_cds_api/) |
| `client/pd-cds-api-bin/` | Native runtime distribution: self-contained `fn-fileget` + `libpacparser.so.1`, per-arch wheels | [Installation](https://dune.github.io/frontier-condb2/installation/) |
| `client/pd-cds-cli/` | `pd-cds` Typer CLI | [CLI guide](https://dune.github.io/frontier-condb2/cli/) |
| `tests/perf/` | Locust perf harness for the client | [Performance testing](https://dune.github.io/frontier-condb2/perf/) |
| `infra/` | Server-side stack: ConDB2 REST API, Frontier server, compose/quadlet | [Runbook](https://dune.github.io/frontier-condb2/infra/runbook/) |
| `scripts/` | `build-frontier-client.sh`, `stage-frontier-client.sh`, `build_simple_index.py`, `gen_api_reference.py` | inline `--help` |
| `FRONTIER_REF` / `VERSION` | Pinned upstream commit / release version | [Releases & maintenance](https://dune.github.io/frontier-condb2/releases/) |
| `docs/` + `zensical.toml` | Zensical docs sources (site content) | [site home](https://dune.github.io/frontier-condb2/) |
| `.github/workflows/` | `frontier-build.yml` → `client.yml` → `release.yml` → `pages.yml` (docs + `/simple/` index) | [Releases & maintenance](https://dune.github.io/frontier-condb2/releases/#cicd) |

## Contributor quickstart

```bash
git clone https://github.com/DUNE/frontier-condb2.git && cd frontier-condb2
make stage          # containerized manylinux_2_28 build of the pinned client
uv sync             # .venv (Python 3.14 via uv); requires uv — see site home
uv run pd-cds --help
```

Targets: `make build / test / lint / smoke / docs / docs-serve` — workflow
details, troubleshooting, and the Pages wheel index:
[docs site](https://dune.github.io/frontier-condb2/).
