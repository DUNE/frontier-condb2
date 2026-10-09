# pd-cds-api

ProtoDUNE Conditions Data Service — Python client API.

Wraps the Frontier client's `fn-fileget` to query run-conditions folders by
timestamp/time-range. The native executable is **not** part of this package:
it ships in the companion `pd-cds-api-bin` distribution (a per-platform wheel
built in CI from the pinned upstream [fermitools/frontier] client), and is
resolved at runtime via `importlib.resources` by `ApiClientState`.

[fermitools/frontier]: https://github.com/fermitools/frontier

```python
from pd_cds_api.conditions import RunConditions
from pd_cds_api.state import ApiClientState
from pd_cds_api.wrapper import ApiClientWrapper

result = ApiClientWrapper(
    conditions=RunConditions(folder="pdunesp.run_conditionstest", t0=25034)
).run_query()
```

## Local development

The native runtime is generated, never committed. Stage it once (needs
podman/docker and network), then build/test:

```bash
make stage          # containerized manylinux_2_28 build of the pinned revision
make build          # wheels + sdists for pd-cds-api, pd-cds-api-bin, pd-cds-cli
make test           # unit tests
make smoke          # install wheels in a throwaway venv, resolve fn-fileget
```

- `FRONTIER_REF` (repo root file) is the source of truth for the upstream
  commit SHA. Bump it in a PR; CI and `make stage` read it automatically
  (override per-run with the `FRONTIER_REF` env var locally, or a repo
  variable / dispatch input in CI). Where to find the SHA and the full
  procedure: [root README — Releases & maintenance](../../README.md#releases--maintenance).
- A clean checkout without staged artifacts fails fast with instructions:
  `ApiClientState().frontier_client_path` raises `FileNotFoundError`, and
  building `pd-cds-api-bin` exits with a message pointing at
  `scripts/stage-frontier-client.sh`.

See [`pd-cds-api-bin/README.md`](../pd-cds-api-bin/README.md) for the native
wheel's contents and tagging, the [root README](../../README.md) for the
fresh-clone quickstart, and `../../.github/workflows/` for the CI build
pipeline. CLI: [`pd-cds-cli/README.md`](../pd-cds-cli/README.md) ·
perf harness: [`tests/perf/README.md`](../../tests/perf/README.md).
