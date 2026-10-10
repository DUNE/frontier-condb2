# Installation

Every release ships per-arch wheels + sdists as individual GitHub Release
assets, listed by a static [PEP 503 index][simple] on GitHub Pages — the
**primary, permanent distribution channel** for this project.

Python ≥3.14, Linux `x86_64` or `aarch64` (manylinux_2_28).

## From the Pages index

The index carries only this project's three distributions, so keep **PyPI as
the primary index** and add ours as an **extra** one:

=== "pip"

    ```bash
    pip install --extra-index-url https://dune.github.io/frontier-condb2/simple/ pd-cds-cli
    ```

=== "uv (tool install)"

    ```bash
    uv tool install --index https://dune.github.io/frontier-condb2/simple/ pd-cds-cli
    ```

=== "pipx"

    ```bash
    pipx install --pip-args=--extra-index-url=https://dune.github.io/frontier-condb2/simple/ pd-cds-cli
    ```

=== "uv (project)"

    Pin the three `pd-cds*` names to our index in `pyproject.toml`; all other
    dependencies stay on PyPI:

    ```toml
    dependencies = ["pd-cds-cli", "pd-cds-api", "pd-cds-api-bin"]

    [[tool.uv.index]]
    name = "pd-cds"
    url = "https://dune.github.io/frontier-condb2/simple/"
    explicit = true

    [tool.uv.sources]
    pd-cds-cli = [{ index = "pd-cds" }]
    pd-cds-api = [{ index = "pd-cds" }]
    pd-cds-api-bin = [{ index = "pd-cds" }]
    ```

    All three must be listed as direct dependencies *and* sources-bound: uv
    applies `tool.uv.sources` only to direct requirements, so with
    `explicit = true` binding just `pd-cds-cli`, its transitive `pd-cds-api`
    requirement would resolve against PyPI — where it does not exist — and
    `uv lock` fails with "pd-cds-api was not found in the package registry".

A bare `--index-url` (replacing PyPI) **fails** — third-party dependencies
(`typer`, `pydantic`, …) are not hosted on our index. Every index link carries
`#sha256=` integrity data; installers reject corrupted artifacts by name.

`pd-cds-cli` pulls `pd-cds-api` and the platform-matching `pd-cds-api-bin`
automatically — installers select the wheel by its `manylinux_2_28_x86_64` /
`manylinux_2_28_aarch64` platform tag, so no manual arch choice is needed.

!!! note "PyPI status"
    Institutional constraints block publishing to pypi.org — possibly
    permanently — so do **not** plan around `pip install pd-cds-cli` from
    PyPI. The twine→PyPI job in `release.yml` is kept dormant and activates
    (without any workflow change) only if that institutional stance is lifted.

## Direct release-asset URLs (pinned / air-gapped)

Each release also attaches the unpacked files individually — pinnable, and
mirrored easily for air-gapped installs:

```bash
pip install https://github.com/DUNE/frontier-condb2/releases/download/v0.2.1/pd_cds_cli-0.2.1-py3-none-any.whl
```

The pure-Python `pd_cds_api` / `pd_cds_cli` wheels alone are not enough at
runtime — also fetch the `pd_cds_api_bin` wheel matching your architecture
from the same release page.

## What the native wheel ships

`pd-cds-api-bin` is the prebuilt native Frontier client runtime delivered to
`pd-cds-api`:

- `fn-fileget` — self-contained executable built reproducibly in a
  `manylinux_2_28` container from the revision pinned in `FRONTIER_REF`
- `libpacparser.so.1` — PAC support, loaded via `dlopen`, resolved through
  the binary's `$ORIGIN` runpath
- `frontier-manifest.json` — provenance record (upstream SHA, glibc audit)

Wheels are platform-specific (`py3-none-manylinux_2_28_<arch>`); CI
hard-gates their contents (`check-wheel-contents`, `auditwheel`). Upstream
code is (c) Fermilab under the Fermitools BSD license.

## Verify the install

```bash
pd-cds --help
pd-cds get-data pdunesp.run_conditionstest --t0 25034
```

Results land in `./pd-cds-data/`. Live queries need FNAL VPN and (recommended)
a local Squid cache on `localhost:3128` — see the
[runbook](infra/runbook.md#frontier-squid-cache-setup-on-a-local-workstation)
and the [CLI guide](cli.md) for full usage.

[simple]: https://dune.github.io/frontier-condb2/simple/
