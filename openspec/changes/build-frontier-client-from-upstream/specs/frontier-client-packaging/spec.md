# Spec Delta

## Purpose

Defines how the native frontier client executable is built reproducibly from upstream, embedded into the Python client packages, distributed as platform-correct installable wheels, and resolved at runtime — including provenance, architecture/glibc targeting, licensing, and local-development parity.

## ADDED Requirements

### Requirement: Native client built from pinned upstream

The system SHALL build the frontier client from a pinned upstream source revision, not from committed in-tree copies or a moving branch, so every artifact is reproducible.

#### Scenario: Pinned revision is used

- **WHEN** the native build runs
- **THEN** it checks out `fermitools/frontier` at an explicitly pinned revision (a commit SHA resolved from a configured reference)
- **AND** the build output records that exact revision for provenance

#### Scenario: No native sources tracked in the repository

- **WHEN** the repository is inspected at HEAD
- **THEN** no upstream frontier sources, objects, shared libraries, or prebuilt `fn-fileget` are committed under the API package
- **AND** only the Python resource-anchor module for the native directory remains tracked

### Requirement: Self-contained native executable

The system SHALL produce an `fn-fileget` executable that carries the frontier client and its build dependencies statically, so it needs no separate frontier shared library and no environment-configured library search path at runtime. PAC-proxy (pacparser) support SHALL remain functional without requiring the operator to configure a library path.

#### Scenario: Runs without a bundled frontier library

- **WHEN** the built `fn-fileget` is executed on a target host that lacks `libfrontier_client.so`
- **THEN** it runs and completes a request without a dynamic-linker error
- **AND** it does not depend on an environment-provided (`LD_LIBRARY_PATH`) search path

#### Scenario: PAC support remains functional

- **WHEN** `fn-fileget` resolves a PAC-based proxy configuration
- **THEN** pacparser support works without the operator setting a library path

### Requirement: Native executable embedded in the API package

The Python API package SHALL bundle the built `fn-fileget` such that a single-package install provides a working executable, resolvable through the package's resource mechanism.

#### Scenario: Resolved after a clean install

- **WHEN** the `pd-cds-api` wheel is installed into a fresh environment
- **THEN** the client resolves an executable `fn-fileget` path from package resources
- **AND** invoking a query reaches the network layer rather than failing because the executable is missing

#### Scenario: Binary included despite being untracked

- **WHEN** the wheel is built with the native executable present only as a generated, git-ignored file
- **THEN** the built wheel still contains the executable

### Requirement: Platform-correct wheels with a lowered compatibility floor

The system SHALL distribute wheels tagged for the architecture and platform ABI they were built for, built against a baseline lower than AlmaLinux 9 to widen compatibility, and covering both `x86_64` and `aarch64`.

#### Scenario: Architecture-specific tagging

- **WHEN** wheels are built for multiple architectures
- **THEN** each wheel carries a platform tag matching its architecture and the baseline ABI
- **AND** no wheel containing native code is tagged as architecture-neutral/universal

#### Scenario: AlmaLinux 9 is a supported target

- **WHEN** a wheel is installed and run on AlmaLinux 9 or newer for the matching architecture
- **THEN** the bundled `fn-fileget` executes successfully

### Requirement: Build provenance manifest

The system SHALL publish provenance metadata with each native build identifying the upstream revision, frontier client version, architecture, and compatibility baseline.

#### Scenario: Provenance recorded

- **WHEN** the native build completes
- **THEN** a machine-readable manifest is produced alongside the artifact
- **AND** it records the pinned upstream revision, the resolved frontier version, target architecture, and glibc/ABI floor

### Requirement: Upstream license and attribution preserved

The system SHALL retain the upstream license and attribution notices in the redistributed package.

#### Scenario: License files shipped

- **WHEN** the wheel is built
- **THEN** it includes the frontier client license and attribution text
- **AND** a clean install exposes those notices as package metadata or data

### Requirement: Reproducible local build and test

A developer SHALL be able to obtain the native executable and build, install, and test the packages locally using the project's standard tooling, mirroring CI.

#### Scenario: Local staging then wheel build

- **WHEN** a developer runs the documented local staging step and then builds the packages
- **THEN** the native executable is placed where the wheel build expects it
- **AND** a locally built wheel installs and resolves the executable the same way CI does

### Requirement: Publication gated on an installable smoke test

The system SHALL publish wheels only after they pass an automated install-and-run smoke test that confirms the native executable resolves and the package imports.

#### Scenario: Smoke test failure blocks publish

- **WHEN** a wheel fails the install-and-run smoke test
- **THEN** it is not published
- **AND** the pipeline reports the failing check
