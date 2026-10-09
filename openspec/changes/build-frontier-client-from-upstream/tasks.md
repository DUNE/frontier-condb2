# Tasks

## 1. Native build recipe (static fn-fileget + pacparser, no upstream fork)

- [x] 1.1 Write a build recipe that, from a `fermitools/frontier` `client/` checkout, runs the needed upstream make targets and then links `fn-fileget` from `fn-fileget.o` + `.libs/*.o` against a vendored static OpenSSL 3.0 with `-static-libstdc++ -static-libgcc` (zlib/expat stay dynamic; object-link pattern mirrors `fn-req.static`, `Makefile:296-297`), and verify with `ldd` that the result needs no `libfrontier_client.so`.
- [x] 1.2 Link `fn-fileget` with `-Wl,-rpath,'$ORIGIN'` and stage `libpacparser.so.1` beside it; verify PAC resolution works from the co-located lib with `LD_LIBRARY_PATH` unset (spec: self-contained executable).
- [x] 1.3 Capture the frontier version (`FN_VER_MAJOR.MINOR` from the Makefile) and the pinned upstream SHA into `frontier-manifest.json`; verify the manifest fields are populated from the actual build.
- [x] 1.4 Wrap the above as a container-runnable build (Docker/Podman) parameterized by `FRONTIER_REF` and target arch; verify it produces `fn-fileget`, `libpacparser.so.1`, licenses, and the manifest in an output dir.

## 2. Packaging restructure (selector + binary distribution + anchor)

- [x] 2.1 Add a new `client/pd-cds-api-bin` distribution (setuptools) whose package data carries `fn-fileget`, `libpacparser.so.1`, and license files; verify a build emits a correctly platform-tagged `py3-none-manylinux_2_28_<arch>` wheel (nvidia-style root layout; see design D4) that passes `check-wheel-contents` and `auditwheel show`.
- [x] 2.2 Change `ApiClientState.bin_path`/`frontier_client_path` anchor to resolve the executable from the `pd-cds-api-bin` resource package and reduce `ld_library_path` to vestigial/no-op for the static binary (`state.py:36-44`); verify `ApiClientState().frontier_client_path` yields an executable path in a staged environment.
- [x] 2.3 Add `pd-cds-api-bin` as a dependency of `pd-cds-api` and confirm the wrapper still builds/invokes `fn-fileget` unchanged (`wrapper.py` subprocess args); verify `run_query` command construction tests still pass.
- [x] 2.4 Configure `pd-cds-api` `uv_build` with `[tool.uv.build-backend] artifacts` so the tracked anchor `bin/__init__.py` and any generated, git-ignored native files are handled per intent; verify `uv build` includes/excludes exactly the expected files (`unzip -l` the wheel).
- [x] 2.5 Add a unit test asserting the resource resolves to an executable for the current platform and that a missing binary produces a clear, typed error; verify it passes locally once staged.

## 3. Remove committed native copies from the repo

- [x] 3.1 Delete the tracked frontier sources/objects/`fn-fileget`/`libfrontier_client.so*`/headers under `client/pd-cds-api/src/pd_cds_api/bin/` except `__init__.py`; verify `git status` shows only `__init__.py` remaining tracked there.
- [x] 3.2 Add `.gitignore` rules for staged native artifacts (`fn-fileget`, `lib*.so*`, build outputs) in both package bin dirs; verify a freshly staged file is ignored but `__init__.py` stays tracked.
- [x] 3.3 Relocate the vendored license/attribution text (`COPYING`, `Fermilab-2009.txt`) to the `pd-cds-api-bin` source-of-truth for packaging; verify they are referenced by the bin package metadata.

## 4. Local development + uv parity

- [x] 4.1 Add `scripts/stage-frontier-client.sh` that builds (or `gh run download`s) the runtime for the host arch into the `pd-cds-api-bin` resource dir; verify running it makes a subsequent `uv build` of `pd-cds-api-bin` succeed on a clean checkout.
- [x] 4.2 Wire a `uv`-run task / `just`/`Make` target so `uv sync`/`uv build` for the workspace invokes staging (or clearly errors with instructions) when the native binary is absent; verify `uv run` in the workspace succeeds after staging.
- [x] 4.3 Document the local build/test flow and the `FRONTIER_REF` pin in the client README(s); verify a fresh contributor following the doc reaches an installable wheel.

## 5. CI — frontier build workflow

- [x] 5.1 Create `.github/workflows/frontier-build.yml` (`workflow_call`) building via task 1.4 across an `x86_64`/`aarch64` matrix in manylinux (native `ubuntu-24.04-arm` runner for arm64); verify it uploads per-arch `frontier-runtime_<ver>_<arch>` artifacts.
- [x] 5.2 Resolve the upstream pin dynamically (dispatch input → optional repo variable → tracked `FRONTIER_REF` file; team decision: the tracked file is the source of truth for reviewable PR bumps, no workflow edits required). Verified: green multi-arch CI run checked out the SHA from `FRONTIER_REF` with no repo variable set, and `frontier-manifest.json` recorded it.
- [x] 5.3 Upload `frontier-manifest.json` per arch inside the runtime artifact; verify the manifest is downloadable with the artifact. (GitHub signed attestations deliberately omitted to keep the reusable-call permission chain at `contents: read`.)

## 6. CI — wheel build + smoke gate

- [x] 6.1 Rewrite `client.yml` to consume frontier-build outputs, stage them into `pd-cds-api-bin`, and run `uv build` for `pd-cds-api`, `pd-cds-api-bin`, and `pd-cds-cli`; verify wheels are uploaded per arch.
- [x] 6.2 Add a fresh-venv install-and-run smoke test (install the platform wheel, resolve `fn-fileget`, invoke a query with no URL expecting usage/error, not ENOENT) as a required check; verify the job fails when the binary is missing or mis-tagged.
- [x] 6.3 Add `auditwheel show`/`check-wheel-contents` as a hard gate on the binary wheel; verify it rejects any wheel falsely claiming manylinux.
- [x] 6.4 Drop the obsolete full-`client/`-tree upload and the inline pacparser/`--privileged` steps from the old flow (pacparser now built in task 1.2); verify the pipeline no longer references them.

## 7. Release + PyPI publication

- [x] 7.1 Extend `release.yml` to a matrix that builds/publishes wheels for all arches; verify the job graph passes `needs` wiring and collects every per-arch wheel.
- [ ] 7.2 Publish wheels + sdist for the three distributions with twine using scoped `PYPI_API_TOKEN`/`TESTPYPI_API_TOKEN` repo secrets (official-actions-only org policy rules out third-party publish actions); verify a dry-run publish against TestPyPI succeeds for one arch before enabling production.
- [x] 7.3 Keep the GitHub Release for the native runtime bundles + manifests; verify release assets include per-arch runtime and wheel artifacts.

## 8. Cross-cutting integration verification

- [x] 8.1 End-to-end on AlmaLinux 9 for each arch: `pip install pd-cds-cli` from the built wheels, run a real/loopback query, confirm data path works and no `LD_LIBRARY_PATH`/`.so` errors; capture as the acceptance check for the capability. (Verified 2026-10-09: green multi-arch CI run incl. fresh-venv smoke; local x86_64 AlmaLinux 9 acceptance with real queries + locust perf run passed.)
- [x] 8.2 Verify reproducibility: rebuild from the same `FRONTIER_REF` and confirm versioned, tagged wheels and matching manifests are produced (no dependence on committed blobs).

## 9. Post-apply quality & developer-experience work (completed in-session)

- [x] 9.1 Expose `frontier_ttl` in the CLI: global `--ttl` (1/2/3, `FRONTIER_TTL` envvar, typer range validation), verbose-panel row; verified `--ttl 3` -> `-R`, `FRONTIER_TTL=1` -> `-r`, out-of-range exits 2.
- [x] 9.2 Fix CLI failure handling: catch `subprocess.CalledProcessError` in `get-data` (clean stderr + `typer.Exit(returncode)`), remove the now-unreachable `returncode != 0` block; verified by `test_client_failure_exits_cleanly` (no traceback).
- [x] 9.3 Google-style docstrings across the public interface + pydantic `Field(description=…)` + `pd_cds_api` re-exports/`__all__`; enable ruff `D` (google convention) workspace-wide with test exemptions; verified ruff clean, pyright 0 errors, descriptions flow to `model_json_schema()`.
- [x] 9.4 Unit-test both client packages: 51 tests, 100% statement coverage (spy fixtures, parametrized matrices, negative validation); root pytest/coverage config + `make coverage`; verified via `make coverage` gate.
- [x] 9.5 Wire quality gates into CI: ruff lint/format, pyright, coverage-gated pytest step in `client.yml` per-arch (after staging); fix `uv sync --with` misuse by locking `pytest-cov` in the root test group; verified locally + actionlint clean.
- [x] 9.6 Interim docs restructure: root README hub with fresh-clone quickstart, runbook `git mv`'d to `infra/README.md` (banner + relative image links repointed), filled CLI README, added `tests/perf/README.md`; verified all relative links/anchors resolve.
- [x] 9.7 Bump `VERSION` + all pyproject versions to 0.2.0 for first pipeline validation (prior `v0.1.0`/`v0.1.1` tags already exist).
- [x] 9.8 Capture deferred recommendations as eight `skip_specs` OpenSpec roadmap stubs (Tier 1 in-process client, Tier 3 caching, server image attestation, server component tests, docs-tooling migration, PR static gate, CLI timestamp/format quirks, glibc-floor evaluation); verified each passes `openspec validate --strict`.

## Workflow follow-up

- Review the change with maintainers; the glibc-floor question now lives in the `evaluate-lower-glibc-floor` stub — resolve there if a wider target is desired.
- Archive the change once the first multi-arch release is published and the acceptance check (8.1) passes.
