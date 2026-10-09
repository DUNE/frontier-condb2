# Design

## Context

See `proposal.md - Why` for motivation. Technical constraints observed in-repo that shape the approach:

- **What the runtime needs today:** `ApiClientState` resolves `fn-fileget` via `importlib.resources` anchored at `pd_cds_api.bin` and exports `ld_library_path` = that same dir (`state.py:36-44`); the wrapper sets `LD_LIBRARY_PATH` for the subprocess (`wrapper.py:40-42`). `fn-fileget` is dynamically linked and shows `libfrontier_client.so.2 => not found` unless that dir is on the path.
- **Upstream build facts** (`client/Makefile` in `fermitools/frontier`, unmodifiable; the vendored copy has been removed from this repo): version is `FN_VER_MAJOR=2` / `FN_VER_MINOR=10.2`; there is an existing **static** link pattern at `fn-req.static` (`Makefile:296-297`) that links `.libs/*.o` + `$(LIBS)` directly instead of `-lfrontier_client`; pacparser is **`dlopen`'d**, not linked (`Makefile:45`, `pacparser-dlopen.c`), and OpenSSL/zlib/expat are normal dynamic deps (`LIBS`, `Makefile:73`).
- **Existing CI** (`client.yml`, `release.yml`): builds from an unpinned upstream `master`, uploads the entire `client/` tree to a GitHub Release, and does **not** build or publish any Python wheel. Organization policy restricts workflow steps to **officially published `actions/*` only** (no third-party marketplace actions).
- **`uv_build` behavior:** emits pure `py3-none-any` wheels and **excludes git-ignored files** from the wheel by default — both matter once `bin/` becomes a generated artifact.

## Goals / Non-Goals

**Goals:**
- Ship installable PyPI wheels for `pd-cds-api` + `pd-cds-cli` with a working native `fn-fileget`, multi-arch (`x86_64`, `aarch64`), with a glibc floor **lower** than AlmaLinux 9.
- Fully reproducible: pinned upstream revision, provenance manifest, no committed native blobs.
- `uv`-based local build/test that mirrors CI.

**Non-Goals:**
- No changes to wrapper query semantics, TTL/caching tiers, or the perf harness (separate capabilities).
- No Windows/macOS targets (Linux manylinux only).
- Not building/using frontier's SQL/`frontier.py` ctypes path (Tier 1 territory, out of scope here).

## Decisions

### D1 — Model B: static `fn-fileget`, built via a CI-only link (no upstream fork)
Build **without editing upstream**: in CI run upstream `make` for only the needed targets (`htclient libfrontier_client.so fn-fileget.o` — plain `all` additionally links `fn-req.static`, whose `LIBS` lack `-lpthread`), then link `fn-fileget.o` + `.libs/*.o` with `-static-libstdc++ -static-libgcc` against a **vendored static OpenSSL 3.0** built inside the image (manylinux ships no `libssl.a`/`libcrypto.a`, and dynamic OpenSSL cannot work cross-distro because the soname changes `libssl.so.10` on el8 → `libssl.so.3` on el9), while zlib/expat stay dynamic (`libz.so.1`/`libexpat.so.1` are stable sonames on every target). Result: one self-contained binary needing no `libfrontier_client.so` and no environment library path. This mirrors `fn-req.static`'s object-link pattern; `-Wl,-rpath,'$ORIGIN'` resolves the co-located `libpacparser.so.1` (D2).
- *Why:* removes the `.so`/`LD_LIBRARY_PATH`/"header staging" class of problems entirely (the user's Model B choice); the binary path in `wrapper.py`/`state.py` is unaffected.
- *Alt: Model A (ship `.so`+symlinks)* — rejected by decision; keeps "not found" bugs and a bigger surface. *Alt: patch upstream Makefile* — rejected; we cannot/should not fork vendored code.

### D2 — PAC support via `$ORIGIN` RPATH, not bundling into the binary
pacparser is `dlopen`'d by name, so a static `fn-fileget` still needs a discoverable `libpacparser.so`. **Decision:** ship `libpacparser.so.1` alongside `fn-fileget` in the binary wheel and link `fn-fileget` with `-Wl,-rpath,'$ORIGIN'` (a linker flag at our CI link step, no source change) so it resolves the co-located lib with **no** env path.
- *Why:* keeps the "no operator-configured library path" guarantee (spec) while retaining PAC (user: required).
- *Alt: build libpacparser statically into fn-fileget* — frontier uses `dlopen`, so static absorption isn't supported without source edits. *Alt: drop PAC* — rejected by user.

### D3 — Shim packaging: pure selector + per-platform binary wheel
Split the native payload into its own distribution (grpcio/scipy-style):
- `pd-cds-api` — pure `py3-none-any` wheel: the existing Python code; declares a dependency on `pd-cds-api-bin`.
- `pd-cds-api-bin` — one **platform-tagged** wheel per architecture (`py3-none-manylinux_2_28_<arch>`; no ABI coupling since the payload is a standalone binary), each containing only `fn-fileget` (+ `libpacparser.so.1`) + license files, exposed as an importable resource package.
- `ApiClientState` anchor moves from `pd_cds_api.bin` → the bin package's resource root (`state.py` `bin_path` updated; `ld_library_path` **removed** — no-op for a static binary — along with the wrapper's `LD_LIBRARY_PATH` injection).
- *Why:* honors the user's "2b" choice; keeps the code wheel genuinely universal; the heavy native blob scales per-platform on PyPI without re-publishing Python code. From the user's view `pip install pd-cds-api` still yields a working executable (spec satisfied).
- *Alt: single package, multiple platform wheels under the same name* — viable and simpler (no anchor change) but re-publishes Python code per arch and forces the API package to be non-pure; rejected to stay within "2b".

### D4 — Build system per distribution
- `pd-cds-api` (selector): stays on `uv_build`, plus `[tool.uv.build-backend] artifacts` so the resource stub dir isn't dropped.
- `pd-cds-api-bin` (native): a minimal `setuptools` backend with a `bdist_wheel` subclass that sets `python_tag="py3"`, `abi_tag="none"`, and a supplied `plat_name=manylinux_2_28_<arch>`, keeping the nvidia-*-cudnn pattern: importable package at wheel root with `Root-Is-Purelib: true`. (Forcing the wheel non-pure instead relocates package data under `.data/purelib/`, which `auditwheel` rejects for shipped ELFs.) Validated with `auditwheel show`/`check-wheel-contents`.
- *Why:* `uv_build` cannot set a platform tag; a `bdist_wheel` subclass with a supplied `plat_name` is the lowest-friction path to correct PEP 425 tags while keeping the auditwheel-acceptable root layout. *Alt: maturin/cibuildwheel* — heavier than needed (Rust/orchestration-focused); revisit only if wheels grow.

### D5 — manylinux base + native ARM runners
Build inside `quay.io/pypa/manylinux_2_28_*` (a container image, not an action; glibc 2.28 ≈ RHEL/Alma 8 baseline, comfortably below AlmaLinux 9) for both `x86_64` and `aarch64`, using the native `ubuntu-24.04` / `ubuntu-24.04-arm` GitHub runners (a qemu-based action would violate the official-actions-only policy; native ARM runners avoid it entirely).
- *Why:* lowers the floor (user) and standardizes the "not found"/glibc story. The image ships **no** static OpenSSL, which is why the build vendors its own pinned static OpenSSL 3.0 (D1) and pins gcc-toolset-11 (pacparser's bundled SpiderMonkey does not build on the image-default gcc 14).
- *Alt: build on AlmaLinux 9* — floor too high for wider reuse. *Alt: full cross-compile toolchain* — more complexity than native ARM runners.

### D6 — CI/CD decomposition (all inputs dynamic)
```
frontier-build.yml (call): checkout pinned FRONTIER_REF -> build static fn-fileget
  (+ libpacparser) in manylinux, per-arch matrix -> upload frontier-runtime_<ver>_<arch>
  + frontier-manifest.json {ref, sha, version, arch, glibc_floor}
client.yml (call, rewritten): per-arch -> download runtime, stage into
  pd-cds-api-bin resource dir -> static gates (ruff check + format --check,
  pyright) + coverage-gated unit tests (pytest --cov-fail-under=85) ->
  uv build (api selector + bin + cli) ->
  fresh-venv smoke test (install wheel; resolve fn-fileget; run query w/o URL
  => expect usage/error, not ENOENT) -> upload wheels
release.yml (extended): matrix across arches -> publish wheels+sdist to PyPI
  via twine + scoped `PYPI_API_TOKEN`/`TESTPYPI_API_TOKEN` repo secrets (the
  official-actions-only policy rules out `pypa/gh-action-pypi-publish`);
  keep GitHub Release for the native bundle
```
Upstream pin lives in a repo variable `FRONTIER_REF` (SHA), so bumping never edits workflow logic; the frontier version is read from the Makefile, not hardcoded. (Fallback order: call input → repo variable → tracked `FRONTIER_REF` file, so local dev and CI share one source of truth.) The `release.yml → server.yml` call leg was later trimmed to the scopes `server.yml` actually uses (`contents`/`packages: write`; the never-exercised `attestations`/`id-token` declarations were removed — image attestation, if wanted, becomes a dedicated follow-up change).

### D7 — Local dev parity (`uv`)
Add `scripts/stage-frontier-client.sh` that runs the **same** manylinux build in Docker/Podman (or `gh run download`s the CI runtime artifact) and drops `fn-fileget`+`libpacparser.so` into the `pd-cds-api-bin` resource dir. Wired as a root `Makefile` (`make stage/build/test/smoke` — `build`/`test` depend on `stage-check`), with a `setup.py` build-time guard that aborts `uv build` with staging instructions when a runtime file is absent, and a typed `FileNotFoundError` (naming the script) from `ApiClientState` at runtime. Document that `uv build` needs staging first. `.gitignore` the staged native files; `__init__.py` anchors stay tracked.

### D8 — Provenance, licensing, security
Publish `frontier-manifest.json` as the provenance record, shipped inside each runtime artifact. Signed GitHub attestations are intentionally omitted from the native-build leg so its reusable-workflow call needs no `attestations`/`id-token` grants (reusable permissions are capped by the calling job); revisit if an org-approved attestation path is wanted later. Redistribute `COPYING`/`Fermilab-2009.txt` as license files of `pd-cds-api-bin` (and reference in metadata). Build timestamps are made deterministic from the pinned commit (`SOURCE_DATE_EPOCH` + `built_at` = commit date), so rebuilds of the same SHA yield byte-identical manifests (ELF bytes may still differ in debug path records).

### D9 — Artifact integrity (post-implementation)
`actions/upload-artifact` silently excludes hidden files — both under directory globs and when listed as explicit paths (confirmed twice in CI: the original dotfile manifest never reached the artifact). The provenance manifest therefore ships as `frontier-manifest.json` (no leading dot; the dot prefix was cosmetic). Two guardrails make any future artifact-layout regression loud instead of mysterious: `frontier-build.yml` verifies all three runtime files exist *before* upload (failing the producing arch job directly), and `client.yml` logs the downloaded artifact contents and pre-checks each required file before staging.

## Risks / Trade-offs

- **No static OpenSSL ships in the manylinux base image** (resolved during apply): vendoring a pinned static OpenSSL 3.0 built in-image is *required*, not optional — dynamic OpenSSL cannot cross el8→el9 (soname `libssl.so.10`→`libssl.so.3`), and its absence in the image was not knowable at planning. Model-A ("also ship `.so`") remains the documented escape hatch.
- **aarch64 build capacity** (resolved): native `ubuntu-24.04-arm` runners are used on both legs; QEMU avoided entirely (official-actions-only policy rules out the qemu setup action anyway).
- **Platform-tag mislabeling** → Mitigation: CI gate asserts the bin wheel filename matches the job's `manylinux_2_28_<arch>` tag, runs `auditwheel show` (non-zero exit = violation; a reported older floor than claimed is accepted as conservative) and `check-wheel-contents` as hard checks before upload.
- **`upload-artifact` silently drops hidden files** (observed twice in CI: directory globs *and* explicit paths) → see D9: manifest is intentionally not a dotfile, with producer- and consumer-side existence guards.
- **Anchor indirection (D3) can silently break resource resolution** → Mitigation: smoke test asserts a resolvable, executable `fn-fileget` after a clean install, on every arch.
- **Removing `bin/` is breaking for existing dev checkouts** → Mitigation: staging script + README/`just` target; CI stages automatically.
- **pacparser `dlopen` name mismatch across distros** → Mitigation: pin the soname we bundle (`libpacparser.so.1`) and `$ORIGIN` rpath so the co-located copy wins.

## Migration Plan

1. Land packaging + `bin/` removal + anchor change + `uv_build` artifacts in one coordinated PR (keeps tree green because CI now stages).
2. Add `frontier-build.yml`; rewire `client.yml`; extend `release.yml`; create `FRONTIER_REF` repo variable + `PYPI_API_TOKEN`/`TESTPYPI_API_TOKEN` repo secrets.
3. Cut a release to publish the first multi-arch wheels.
4. **Rollback:** the previous tagged release (committed `bin/`) remains installable from history; re-enable a bundled-binary path by repointing the anchor if the shim approach must be reverted.

## Open Questions

- ~~Exact glibc floor: `manylinux_2_28` (RHEL8) vs a still-lower `2_17` for legacy EL7~~ — deferred to the `evaluate-lower-glibc-floor` roadmap stub; `2_28` ships (auditwheel reports the actual floor as `2_26`, so the tag is conservative).
- ~~Whether to also publish `py3-none-any` sdists for the bin package~~ — resolved: `uv build` emits sdists for all three distributions and the twine step uploads `wheels/*` (sdists included).
