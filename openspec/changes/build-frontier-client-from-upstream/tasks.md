# Tasks

## 1. Native build recipe (static fn-fileget + pacparser, no upstream fork)

- [x] 1.1 Write a build recipe that, from a `fermitools/frontier` `client/` checkout, runs `make` and then links `fn-fileget` from `fn-fileget.o` + `.libs/*.o` against static OpenSSL/zlib/expat (mirroring `fn-req.static`, `Makefile:296-297`), and verify with `ldd` that the result needs no `libfrontier_client.so`.
- [x] 1.2 Link `fn-fileget` with `-Wl,-rpath,'$ORIGIN'` and stage `libpacparser.so.1` beside it; verify PAC resolution works from the co-located lib with `LD_LIBRARY_PATH` unset (spec: self-contained executable).
- [x] 1.3 Capture the frontier version (`FN_VER_MAJOR.MINOR` from the Makefile) and the pinned upstream SHA into `frontier-manifest.json`; verify the manifest fields are populated from the actual build.
- [x] 1.4 Wrap the above as a container-runnable build (Docker/Podman) parameterized by `FRONTIER_REF` and target arch; verify it produces `fn-fileget`, `libpacparser.so.1`, licenses, and the manifest in an output dir.

## 2. Packaging restructure (selector + binary distribution + anchor)

- [x] 2.1 Add a new `client/pd-cds-api-bin` distribution (setuptools) whose package data carries `fn-fileget`, `libpacparser.so.1`, and license files; verify a `--plat-name manylinux_2_28_<arch>` build emits a non-pure, correctly-tagged wheel.
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

- [x] 5.1 Create `.github/workflows/frontier-build.yml` (`workflow_call`) building via task 1.4 across an `x86_64`/`aarch64` matrix in manylinux (QEMU for arm64); verify it uploads per-arch `frontier-runtime_<ver>_<arch>` artifacts.
- [ ] 5.2 Read the upstream pin from a repo variable `FRONTIER_REF` (no workflow logic edits to bump); verify changing the variable changes the checked-out SHA recorded in the manifest.
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

- [ ] 8.1 End-to-end on AlmaLinux 9 for each arch: `pip install pd-cds-cli` from the built wheels, run a real/loopback query, confirm data path works and no `LD_LIBRARY_PATH`/`.so` errors; capture as the acceptance check for the capability.
- [x] 8.2 Verify reproducibility: rebuild from the same `FRONTIER_REF` and confirm versioned, tagged wheels and matching manifests are produced (no dependence on committed blobs).

## Workflow follow-up

- Review the change with maintainers; resolve design Open Questions (glibc floor `2_28` vs `2_17`) if a wider target is desired before or shortly after archive.
- Archive the change once the first multi-arch release is published and the acceptance check (8.1) passes.
