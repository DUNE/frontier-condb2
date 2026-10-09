# ProtoDUNE Conditions Data Service (frontier-condb2)

Client, server infrastructure, and perf tests for the ProtoDUNE run-conditions
database, served through the [Frontier](https://frontier.cern.ch) stack and a
ConDB2 REST backend.

> **Interim docs.** This layout is a deliberate stopgap (hub README + linked
> leaf READMEs) and will be replaced by a proper docs tool later. Each area's
> doc is authoritative for that area; links below.

## Repository map

| Path | What it is | Docs |
|---|---|---|
| `client/pd-cds-api/` | Python API wrapping `fn-fileget` (RunConditions/ApiClientState/ApiClientWrapper) | [README](client/pd-cds-api/README.md) |
| `client/pd-cds-api-bin/` | Native runtime distribution: self-contained `fn-fileget` + `libpacparser.so.1`, per-arch wheels | [README](client/pd-cds-api-bin/README.md) |
| `client/pd-cds-cli/` | `pd-cds` Typer CLI | [README](client/pd-cds-cli/README.md) |
| `tests/perf/` | Locust perf harness for the client | [README](tests/perf/README.md) |
| `infra/` | Server-side stack: ConDB2 REST API, Frontier server, compose/quadlet | [Runbook](infra/README.md) |
| `scripts/` | `build-frontier-client.sh` (containerized native build), `stage-frontier-client.sh` | inline `--help` |
| `FRONTIER_REF` | Pinned `fermitools/frontier` commit SHA used by `make stage` and CI | — |
| `VERSION` | Release version (GitHub tag; pyproject versions kept in lockstep) | — |
| `.github/workflows/` | `frontier-build.yml` → `client.yml` (wheels, gates, smoke) → `release.yml` (PyPI + GitHub Release), `server.yml` (images) | — |

## Quickstart (fresh clone → working CLI + perf run)

### Prerequisites

- Linux on `x86_64` or `aarch64` (AlmaLinux/Rocky/RHEL 9+ is the primary target)
- `git`, and a container runtime for staging: `podman` or `docker`
- [uv](https://docs.astral.sh/uv/) (manages the Python ≥3.14 toolchain itself):
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh && source ~/.local/bin/env
  ```
- For **live queries**: FNAL VPN and (recommended) a local Squid cache proxy on
  `localhost:3128` — set up via the [runbook: Frontier Squid Cache Setup on a
  Local Workstation](infra/README.md#frontier-squid-cache-setup-on-a-local-workstation)

### 0. Clone and stage the native runtime

The Frontier client binary is **never committed** — it is built reproducibly in
a `manylinux_2_28` container from the revision pinned in `FRONTIER_REF`:

```bash
git clone https://github.com/DUNE/frontier-condb2.git && cd frontier-condb2
make stage          # ~5 min, first run pulls the manylinux image
uv sync             # creates .venv (Python 3.14 fetched by uv if needed)
```

Verify anytime with `make stage-check` (`scripts/stage-frontier-client.sh
--from-ci <run-id>` downloads a CI-built runtime instead of compiling).

### 1. Run the CLI

Global options come **before** the subcommand; output format defaults to `csv`:

```bash
uv run pd-cds --help
uv run pd-cds -v get-data pdunesp.run_conditionstest --t0 25034
uv run pd-cds get-data pdunesp.run_conditionstest --t0 25100 --t1 25115
```

Results land in `./pd-cds-data/<folder>-t_<t0>.csv`. Full reference:
[client/pd-cds-cli/README.md](client/pd-cds-cli/README.md).

### 2. Run the Locust perf tests

```bash
uv run locust -f tests/perf/locustfile.py --processes -1            # Web UI :8089
uv run locust -f tests/perf/locustfile.py --processes -1 \
    --headless -u 50 -r 10 -t 60s                                   # scripted run
```

`--processes -1` fans out one worker per core. Details, task layout, and
target overrides: [tests/perf/README.md](tests/perf/README.md).

### 3. Build wheels / test the distribution path

```bash
make build     # wheels + sdists for all three distributions → dist/
make test      # unit tests
make lint      # ruff
make smoke     # throwaway venv: install dist/ wheels, resolve fn-fileget, CLI --help
```

## CI/CD

`frontier-build.yml` builds the static runtime per-arch (native ARM runner) and
uploads `frontier-runtime_<ver>_<arch>` artifacts (+ provenance manifest) →
`client.yml` stages them, builds platform-tagged wheels, hard-gates with
`check-wheel-contents`/`auditwheel`, and smoke-installs each arch →
`release.yml` publishes to PyPI via twine (API-token secrets; TestPyPI
dry-runs available through `workflow_dispatch`) and cuts the GitHub Release.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `Native Frontier runtime is missing...` | Run `make stage` (needs podman/docker + network) |
| `FileNotFoundError: Frontier client 'fn-fileget' not found in package...` | Same — runtime not staged in this workspace |
| CLI query: `Network is unreachable` / proxy connect errors | VPN down, or no local Squid on :3128 — see [infra runbook](infra/README.md) |
| Locust errors on every request | Same prerequisites as live CLI queries |
| Wheel install: `not a supported wheel on this platform` | Wheels are per-arch `manylinux_2_28_*`; match your platform or `make stage && make build` locally |
