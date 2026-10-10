# Proposal

## Why

A `release.yml` run on main failed because the runner pool exhausted Docker Hub's **anonymous pull rate limit** (100 pulls/repo/6h per egress IP; GitHub-hosted runners share IPs). Every CI path that references `docker.io` images is exposed the same way, and the failure mode lands on the release critical path: the release job's completion is what triggers the `workflow_run` Pages deploy that refreshes the `/simple/` wheel index. The fix: serve the hot base images from GHCR — pulls of public `ghcr.io` packages are unlimited, the org already pushes there (so credentials/permissions exist), and no third-party actions are needed.

## What Changes

- Publish mirror copies of the Docker Hub base images CI pulls into a public package namespace under `ghcr.io/DUNE/` (candidate set from audit: `almalinux:9`, `almalinux:9-minimal`, `almalinux/9-init` — the `server.yml` **job container** plus `infra/condb2_rest_api/Dockerfile` and `infra/frontier_server/Dockerfile` bases).
- Repoint all CI-reachable references from `docker.io/...` to the GHCR mirrors (`server.yml` container image; the two Dockerfile `FROM` lines). Local/non-CI users keep working: GHCR pulls need no login for public packages.
- A small refresh workflow (official `actions/*` + `skopeo`/`podman` run-steps on `schedule:`/`workflow_dispatch`) to re-push mirrors when upstream tags move; pin mirrors by digest and make the repointed `FROM`s/digests an explicit freshness decision (the current `9-init:latest` mutability is itself a supply-chain smell worth fixing here).
- Out of scope: `quay.io/pypa/manylinux_2_28_*` (`build-frontier-client.sh`) — quay.io has no comparable anonymous cap; the authenticated-pull alternative (Docker Hub PAT secret) is rejected as per-account-quota, secret-bearing, and still third-party-throttled.

## Capabilities

### New Capabilities
- (intended) None behaviorally; CI supply-chain hardening — `skip_specs: true` at planning; revisit at design time if the digest-pinning rules turn into observable release guarantees.

### Modified Capabilities
- (none — `server-image-provenance`/`frontier-client-packaging` outputs are unchanged; only *where* build inputs are pulled from moves.)

## Impact

- `.github/workflows/server.yml` (container image ref; new mirror-refresh workflow alongside), `infra/condb2_rest_api/Dockerfile`, `infra/frontier_server/Dockerfile`, one-time `podman/skopeo copy` seeding (developer machine or dispatched workflow).
- Docs touch: infra runbook + `docs/releases.md` CI/CD note (build inputs now sourced from GHCR; upstream-sync procedure documented).
- Depends on nothing from the #31 changes; complements them by de-risking the `workflow_run` index-refresh edge.

Context: raised during #31 post-merge verification (first main `release.yml` run failed on Docker Hub rate-limit); captured here for later per user request — design/tasks deferred deliberately.
