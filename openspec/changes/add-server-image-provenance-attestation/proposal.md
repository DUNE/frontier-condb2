# Proposal

## Why

During the CI/CD permission-chain work, `server.yml` had unused `attestations`/`id-token` grants removed (Option A: least privilege). The alternative — actually signing provenance for the deployed container images — was valued (facility-hosted ConDB2/Frontier stack) but explicitly deferred as its own change (Option B).

## What Changes

- After `podman push` in `server.yml`, capture each pushed image's manifest digest (`:v<version>` tags; not `:latest`) and run `actions/attest-build-provenance@v4` with `subject-name`/`subject-digest`/`push-to-registry: true` so signed attestations land in GHCR as OCI referrers.
- Re-grant `attestations: write` + `id-token: write` at the server-call job and in `server.yml`.
- Document consumer verification (`gh attestation verify oci://…`) in the infra runbook; decide policy for multi-arch images if ever introduced.

## Capabilities

### New Capabilities
- (intended) `server-image-provenance`: attestation presence/verification behavior for published images. To be delta'd at planning.

### Modified Capabilities
- (none)

## Impact

`.github/workflows/server.yml`, `release.yml` call-leg permissions, infra runbook. Source: Option A/B evaluation during the official-actions-only refactor.
