# documentation-site Specification

## Purpose

Specify the externally observable guarantees of the project documentation site: how it publishes onto GitHub Pages alongside the wheel index without clobbering it, what blocks a merge, and how the API reference is kept honest with the code.

## Requirements

### Requirement: Single composed Pages publisher

The project SHALL operate exactly one GitHub Pages deployer for the repository site. That deployer publishes the documentation tree at the site root while preserving `/simple/**` exclusively for the package index; no other workflow may deploy Pages, and the deploy SHALL complete via official GitHub actions only.

#### Scenario: Docs deploy never removes the index

- **WHEN** any documentation-only change is deployed
- **THEN** `/simple/**` content is still present in the resulting site, regenerated as part of the same deployment

#### Scenario: Index deploy never removes the docs

- **WHEN** a deployment is triggered by release completion rather than a docs change
- **THEN** the full documentation site is published unchanged alongside the refreshed index

### Requirement: Atomic co-publication

Each documentation and package index content SHALL be published as one composed deployment artifact, so no observable intermediate site state exists where one producer's content is missing or stale relative to the other's.

#### Scenario: Path-ownership enforcement

- **WHEN** a build would cause the documentation output and the index output to collide (documentation emitting files under `/simple/**`, or the index generator writing outside it)
- **THEN** the deployment pipeline fails before publishing rather than producing a mixed-ownership site

### Requirement: Strict validation gate on merges

A pull request SHALL NOT be mergeable-green unless the documentation builds with validation strict enough to fail on warnings and dead internal links, and unless generated reference content matches its source packages.

#### Scenario: Dead link blocks the gate

- **WHEN** a proposed docs change links to a page, anchor, or asset that does not exist
- **THEN** the PR check fails with the offending location identified

#### Scenario: Reference drift blocks the gate

- **WHEN** the committed generated API pages no longer match what the generator produces from current package sources
- **THEN** the PR check fails and names the regeneration remedy

### Requirement: Derived API reference

The site SHALL expose an API reference for each importable client distribution generated from that code's own docstrings and field metadata — including structured descriptions declared in the code, not only prose comments — with no hand-maintained per-module stub pages, and the reference build SHALL NOT require the platform-native runtime the packages execute at query time.

#### Scenario: Public API surface appears without manual pages

- **WHEN** a class or function is public in a documented package
- **THEN** it appears in the reference with its docstring and structured field descriptions rendered, produced by the build rather than authored by hand

#### Scenario: Docs build on a runtime-less checkout

- **WHEN** the reference is built in an environment without the staged native client runtime
- **THEN** the build succeeds; only actually executing queries would require it
