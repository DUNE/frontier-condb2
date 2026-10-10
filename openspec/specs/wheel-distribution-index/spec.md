# wheel-distribution-index Specification

## Purpose

Makes the project's Python distributions installable through standard tooling (pip, uv, pipx) by publishing them as a static PEP 503 package index on GitHub Pages, with direct-download release assets as a complementary channel, without depending on an external package index.

## Requirements

### Requirement: Installable package index

The system SHALL expose each published distribution (`pd-cds-api`, `pd-cds-api-bin`, `pd-cds-cli`) through a PEP 503 simple-repository index served from the project's GitHub Pages site, so standard installers can resolve and fetch it as an additional index alongside PyPI (which continues to serve third-party dependencies).

#### Scenario: Fresh-environment install from the index

- **WHEN** a user installs `pd-cds-cli` with pip (or uv) referencing the Pages index as an extra index on a supported Linux platform
- **THEN** the installer resolves `pd-cds-cli`, `pd-cds-api`, and the platform-matching `pd-cds-api-bin` wheel from that index, resolves dependencies from PyPI, and the installed CLI executes

### Requirement: Release-triggered index publication

The system SHALL update the published index automatically as part of the release workflow, with no manual steps, and the update SHALL be idempotent (re-running it for the same release produces an equivalent index).

#### Scenario: New release appears in the index

- **WHEN** a release completes in CI for a new version
- **THEN** the index pages list that version's wheels and sdists without operator intervention

#### Scenario: Rerun after a failed deploy

- **WHEN** the publication step is re-run for an already-released version
- **THEN** the resulting index contains each artifact exactly once and installs still succeed

### Requirement: Index correctness and integrity metadata

The index SHALL use PEP 503 normalized project names, reference artifacts by downloadable URL with `sha256` fragment integrity data, and only list files produced by the CI release flow.

#### Scenario: Tampered or corrupted artifact

- **WHEN** a download served via the index does not match its declared sha256
- **THEN** the installer rejects the file and the error names the artifact

### Requirement: Per-platform wheel selection

Because wheels carry platform tags (`manylinux_2_28_x86_64`, `manylinux_2_28_aarch64`), the index SHALL enable installers to select the wheel matching the consumer's platform and reject incompatible ones.

#### Scenario: x86_64 consumer resolves x86_64 binary wheel

- **WHEN** pip resolves `pd-cds-api-bin` from the index on `x86_64` Linux
- **THEN** the selected wheel is the `manylinux_2_28_x86_64` build

### Requirement: Direct-URL release assets

Each GitHub Release SHALL additionally attach unpacked `.whl` and `.tar.gz` files (not only zip bundles) so they can be pinned and installed by direct URL.

#### Scenario: Air-gapped or pinned install

- **WHEN** a user downloads a specific release's wheel file and runs `pip install ./pd_cds_cli-<ver>-py3-none-any.whl`
- **THEN** installation succeeds without network access to any index

### Requirement: Distribution channel independence

GitHub Pages index publication SHALL NOT depend on PyPI credentials; the existing twine→PyPI publish remains an optional additional channel that is skipped (not failed) when its secrets are absent.

#### Scenario: Release with no PyPI tokens configured

- **WHEN** a release runs without `PYPI_API_TOKEN`
- **THEN** the Pages index still updates and the pipeline stays green

### Requirement: Documented install channels

The project documentation SHALL provide copy-pasteable install instructions for pip, uv (project-level index configuration and `uv tool install`), and pipx, pointing at the index URL, and record the direct-URL alternative.

#### Scenario: New collaborator installs the CLI

- **WHEN** a contributor follows the documented install commands on a supported platform
- **THEN** `pd-cds --help` runs, without them needing to know any PyPI account exists
