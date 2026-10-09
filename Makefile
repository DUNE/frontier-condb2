# ProtoDUNE Conditions Data Service — client development
#
# The native Frontier runtime is never committed. Stage it first (requires
# podman or docker and network access), then build/test as usual.

UV ?= uv

.PHONY: stage stage-check build test test-scripts coverage lint docs docs-gen docs-serve smoke check-versions clean

## Stage the pinned fermitools/frontier build into pd-cds-api-bin (containerized)
stage:
	scripts/stage-frontier-client.sh

stage-check:
	scripts/stage-frontier-client.sh --check

## Build wheels + sdists for api, api-bin, cli into dist/
build: stage-check
	rm -rf dist && mkdir -p dist
	cd client/pd-cds-api && $(UV) build --out-dir ../../dist
	cd client/pd-cds-api-bin && $(UV) build --out-dir ../../dist
	cd client/pd-cds-cli && $(UV) build --out-dir ../../dist

## Unit tests (all workspace packages; testpaths set in root pyproject)
test: stage-check
	$(UV) run --group test pytest -v

## Index-generator unit tests (stdlib-only; no staged runtime needed)
test-scripts:
	$(UV) run --group test pytest -v scripts/tests

## Unit tests with statement coverage gate over both client packages
coverage: stage-check
	$(UV) run --group test python -m pytest \
		--cov=pd_cds_api --cov=pd_cds_cli --cov-report=term-missing \
		--cov-fail-under=85

lint:
	$(UV) run ruff check client/ tests/ scripts/
	$(UV) run ruff format --check client/ tests/

## Build the Zensical docs site (strict: fails on warnings/dead links) -> site/
docs: docs-gen
	$(UV) run --group docs zensical build --clean --strict

## Regenerate committed docs/reference/ pages from the client packages
docs-gen:
	python3 scripts/gen_api_reference.py

## Live-preview the docs site (http://localhost:8000)
docs-serve:
	$(UV) run --group docs zensical serve

## Install built wheels into a throwaway venv and resolve fn-fileget
smoke: build
	rm -rf /tmp/pd-cds-smoke
	$(UV) venv /tmp/pd-cds-smoke
	$(UV) pip install --python /tmp/pd-cds-smoke/bin/python \
		dist/pd_cds_api-*.whl dist/pd_cds_api_bin-*.whl dist/pd_cds_cli-*.whl
	/tmp/pd-cds-smoke/bin/python -c "import os; from pd_cds_api.state import ApiClientState; p = ApiClientState().frontier_client_path; assert os.access(p, os.X_OK), p; print('smoke OK:', p)"
	/tmp/pd-cds-smoke/bin/pd-cds --help > /dev/null && echo "CLI entry point OK"

## Verify VERSION and all pyproject versions agree (run before releasing)
check-versions:
	python3 scripts/check-versions.py

clean:
	rm -rf dist client/*/dist client/*/.venv
	rm -rf /tmp/pd-cds-smoke
