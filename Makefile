# ProtoDUNE Conditions Data Service — client development
#
# The native Frontier runtime is never committed. Stage it first (requires
# podman or docker and network access), then build/test as usual.

UV ?= uv

.PHONY: stage stage-check build test lint smoke clean

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

## Unit tests (workspace)
test: stage-check
	$(UV) run --group test pytest client/pd-cds-api/tests -v

lint:
	$(UV) run ruff check client/ tests/ scripts/

## Install built wheels into a throwaway venv and resolve fn-fileget
smoke: build
	rm -rf /tmp/pd-cds-smoke
	$(UV) venv /tmp/pd-cds-smoke
	$(UV) pip install --python /tmp/pd-cds-smoke/bin/python \
		dist/pd_cds_api-*.whl dist/pd_cds_api_bin-*.whl dist/pd_cds_cli-*.whl
	/tmp/pd-cds-smoke/bin/python -c "import os; from pd_cds_api.state import ApiClientState; p = ApiClientState().frontier_client_path; assert os.access(p, os.X_OK), p; print('smoke OK:', p)"
	/tmp/pd-cds-smoke/bin/pd-cds --help > /dev/null && echo "CLI entry point OK"

clean:
	rm -rf dist client/*/dist client/*/.venv
	rm -rf /tmp/pd-cds-smoke
