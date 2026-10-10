# Spec Delta

## Purpose

Extends the wheel distribution capability with continuous proof that the published index remains consumable — failures that originate outside the repository (Pages serving, release-asset retention, API-shape drift) must be detected by the project, not by its users.

## ADDED Requirements

### Requirement: Continuous index installability monitoring

The system SHALL automatically verify — after every release-triggered Pages deployment and at least weekly — that the published simple index remains installable end-to-end, failing visibly on any regression.

#### Scenario: Integrity-validated fetch of every artifact

- **WHEN** the smoke verification runs
- **THEN** each of the three distributions is installed from the live index with its declared `sha256` digest validated against the fetched bytes

#### Scenario: Documented install path executes

- **WHEN** the smoke verification runs
- **THEN** a fresh-environment install of `pd-cds-cli` resolves index-provided packages alongside PyPI dependencies as documented and the CLI executes

#### Scenario: Cross-platform selection

- **WHEN** the smoke verification queries the index as an aarch64 consumer
- **THEN** selection resolves the `manylinux_2_28_aarch64` build

#### Scenario: Rotting links detected without a user

- **WHEN** a referenced release asset disappears or an upstream API change corrupts the published index
- **THEN** the weekly scheduled verification fails within seven days, naming the failing distribution

#### Scenario: Monitoring never blocks publication

- **WHEN** the smoke verification fails
- **THEN** the already-completed site deployment stands; only the workflow run is marked failed (the smoke runs strictly after publish)
