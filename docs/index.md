# ProtoDUNE Conditions Data Service

Client, server infrastructure, and perf tests for the ProtoDUNE run-conditions
database, served through the [Frontier](https://frontier.cern.ch) stack and a
ConDB2 REST backend.

This site is the canonical home for all project prose. The three
distributions install from the project's [PEP 503 wheel index][simple] on
GitHub Pages — see [Installation](installation.md).

[simple]: https://dune.github.io/frontier-condb2/simple/

## Repository map

| Path | What it is | Docs |
|---|---|---|
| `client/pd-cds-api/` | Python API wrapping `fn-fileget` (RunConditions/ApiClientState/ApiClientWrapper) | [API reference][api] |
| `client/pd-cds-api-bin/` | Native runtime distribution: self-contained `fn-fileget` + `libpacparser.so.1`, per-arch wheels | [Installation](installation.md#what-the-native-wheel-ships) |
| `client/pd-cds-cli/` | `pd-cds` Typer CLI | [CLI guide](cli.md) |
| `tests/perf/` | Locust perf harness for the client | [Performance testing](perf.md) |
| `infra/` | Server-side stack: ConDB2 REST API, Frontier server, compose/quadlet | [Runbook](infra/runbook.md) |
| `scripts/` | `build-frontier-client.sh`, `stage-frontier-client.sh` | inline `--help` ([source](https://github.com/DUNE/frontier-condb2/tree/main/scripts)) |
| `FRONTIER_REF` / `VERSION` | Pinned upstream commit / release version (lockstep, see below) | [Releases & maintenance](releases.md) |
| `.github/workflows/` | `frontier-build.yml` → `client.yml` → `release.yml` → `pages.yml` (this site + [wheel index][simple]) | [Releases & maintenance](releases.md#cicd) |

[api]: reference/pd_cds_api.md

## Choose your path

**I want to run queries** → [Installation](installation.md), then the
[CLI guide](cli.md). Python ≥3.14 on Linux `x86_64`/`aarch64`
(AlmaLinux/Rocky/RHEL 9+ is the primary target). Live queries need FNAL VPN
and (recommended) a local Squid cache on `localhost:3128` — set one up via the
[runbook](infra/runbook.md#frontier-squid-cache-setup-on-a-local-workstation).

**I want to contribute** — fresh clone → working CLI + perf run:

```bash
git clone https://github.com/DUNE/frontier-condb2.git && cd frontier-condb2
make stage          # ~5 min: containerized manylinux_2_28 build of FRONTIER_REF
uv sync             # creates .venv (Python 3.14 fetched by uv if needed)
uv run pd-cds --help
```

The native Frontier client binary is **never committed** — `make stage`
builds it reproducibly from the pinned revision; verify anytime with
`make stage-check` (`scripts/stage-frontier-client.sh --from-ci <run-id>`
downloads a CI-built runtime instead of compiling). Daily driver targets:

```bash
make build          # wheels + sdists for all three distributions → dist/
make test           # unit tests (workspace packages)
make lint           # ruff
make smoke          # throwaway venv: install dist/ wheels, resolve fn-fileget
make docs           # strict docs build (this site) → site/
make docs-serve     # live preview at http://localhost:8000
```

Requires [uv](https://docs.astral.sh/uv/) (`curl -LsSf
https://astral.sh/uv/install.sh | sh`) and podman or docker for staging.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `Native Frontier runtime is missing...` | Run `make stage` (needs podman/docker + network) |
| `FileNotFoundError: Frontier client 'fn-fileget' not found in package...` | Same — runtime not staged in this workspace |
| CLI query: `Network is unreachable` / proxy connect errors | VPN down, or no local Squid on :3128 — see [runbook](infra/runbook.md) |
| Locust errors on every request | Same prerequisites as live CLI queries |
| Wheel install: `not a supported wheel on this platform` | Wheels are per-arch `manylinux_2_28_*`; match your platform or `make stage && make build` locally |

## License

Frontier client code is (c) Fermilab under the Fermitools BSD license (see
`COPYING` / `Fermilab-2009.txt` in `client/pd-cds-api-bin/`).
