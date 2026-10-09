# Proposal

## Why

The client packages now have a coverage-gated test suite, but `infra/condb2_rest_api` (its own pyproject/uvicorn service, config templating, quadlet units) has **zero tests** and `server.yml` builds/publishes images without any test step. Flagged during the unit-testing evaluation as out of that change's scope.

## What Changes

- Establish a test harness for the ConDB2 REST API service (pytest + httpx/TestClient against the service; config templating tests for the `dune_runcon_prod.yaml` placeholder substitution done in `server.yml`).
- Add a test step to the `server.yml` pipeline (mirroring the client job's static-check + coverage pattern).
- Decide fixture strategy for ConDB2/Frontier backends (recorded responses vs loopback containers via compose).

## Capabilities

### New Capabilities
- (intended) `condb2-rest-api-service`: currently undocumented in specs at all; planning should first capture baseline behavior, then test-driven requirements. To be delta'd at planning.

### Modified Capabilities
- (none)

## Impact

`infra/condb2_rest_api/` (new tests + dev-group deps), `.github/workflows/server.yml`. Source: gap noted during the client unit-testing evaluation ("server.yml / infra have no tests — future change").
