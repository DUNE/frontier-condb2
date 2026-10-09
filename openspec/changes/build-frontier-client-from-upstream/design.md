# Design

## Context

See `proposal.md - Why` for motivation. Technical constraints observed in-repo that shape the approach:

- **What the runtime needs today:** `ApiClientState` resolves `fn-fileget` via `importlib.resources` anchored at `pd_cds_api.bin` and exports `ld_library_path` = that same dir (`state.py:36-44`); the wrapper sets `LD_LIBRARY_PATH` for the subprocess (`wrapper.py:40-42`). `fn-fileget` is dynamically linked and shows `libfrontier_client.so.2 => not found` unless that dir is on the path.
- **Upstream build facts** (`bin/Makefile`, unmodifiable — it is vendored from `fermitools/frontier`): version is `FN_VER_MAJOR=2` / `FN_VER_MINOR=10.2`; there is an existing **static** link pattern at `fn-req.static` (`Makefile:296-297`) that links `.libs/*.o` + `$(LIBS)` directly instead of `-lfrontier_client`; pacparser is **`dlopen`'d**, not linked (`Makefile:45`, `pacparser-dlopen.c`), and OpenSSL/zlib/expat are normal dynamic deps (`LIBS`, `Makefile:73`).
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
Reproduce the `fn-req.static` recipe for fileget **without editing upstream**: in CI run `make` (produces objects + `.libs/`), then invoke the compiler directly to link `fn-fileget.o .libs/*.o` against **static** OpenSSL/zlib/expat (`-Wl,-Bstatic … -Wl,-Bdynamic`), yielding one self-contained binary that needs no `libfrontier_client.so`.
- *Why:* removes the `.so`/`LD_LIBRARY_PATH`/"header staging" class of problems entirely (the user's Model B choice); the binary path in `wrapper.py`/`state.py` is unaffected.
- *Alt: Model A (ship `.so`+symlinks)* — rejected by decision; keeps "not found" bugs and a bigger surface. *Alt: patch upstream Makefile* — rejected; we cannot/should not fork vendored code.

### D2 — PAC support via `$ORIGIN` RPATH, not bundling into the binary
pacparser is `dlopen`'d by name, so a static `fn-fileget` still needs a discoverable `libpacparser.so`. **Decision:** ship `libpacparser.so.1` alongside `fn-fileget` in the binary wheel and link `fn-fileget` with `-Wl,-rpath,'$ORIGIN'` (a linker flag at our CI link step, no source change) so it resolves the co-located lib with **no** env path.
- *Why:* keeps the "no operator-configured library path" guarantee (spec) while retaining PAC (user: required).
- *Alt: build libpacparser statically into fn-fileget* — frontier uses `dlopen`, so static absorption isn't supported without source edits. *Alt: drop PAC* — rejected by user.

### D3 — Shim packaging: pure selector + per-platform binary wheel
Split the native payload into its own distribution (grpcio/scipy-style):
- `pd-cds-api` — pure `py3-none-any` wheel: the existing Python code; declares a dependency on `pd-cds-api-bin`.
- `pd-cds-api-bin` — one **platform-tagged** wheel per (arch × ABI), each containing only `fn-fileget` (+ `libpacparser.so.1`) + license files, exposed as an importable resource package.
- `ApiClientState` anchor moves from `pd_cds_api.bin` → the bin package's resource root (`state.py` `bin_path`/`ld_library_path` updated; `ld_library_path` becomes vestigial for a static binary).
- *Why:* honors the user's "2b" choice; keeps the code wheel genuinely universal; the heavy native blob scales per-platform on PyPI without re-publishing Python code. From the user's view `pip install pd-cds-api` still yields a working executable (spec satisfied).
- *Alt: single package, multiple platform wheels under the same name* — viable and simpler (no anchor change) but re-publishes Python code per arch and forces the API package to be non-pure; rejected to stay within "2b".

### D4 — Build system per distribution
- `pd-cds-api` (selector): stays on `uv_build`, plus `[tool.uv.build-backend] artifacts` so the resource stub dir isn't dropped.
- `pd-cds-api-bin` (native): a minimal `setuptools` backend that emits a real platform tag (`build --plat-name manylinux_2_28_<arch>` / a `bdist_wheel` subclass setting `root_is_purelib=False`), then validated with `auditwheel show`/`check-wheel-contents`.
- *Why:* `uv_build` cannot set a platform tag; `setuptools`' `--plat-name` is the lowest-friction path to correct PEP 425 tags. *Alt: maturin/cibuildwheel* — heavier than needed (Rust/orchestration-focused); revisit only if wheels grow.

### D5 — manylinux base + cross-arch via QEMU
Build inside `quay.io/pypa/manylinux_2_28_*` (a container image, not an action) (glibc 2.28 ≈ RHEL/Alma 8 baseline, comfortably below AlmaLinux 9) for both `x86_64` and `aarch64`, using the native `ubuntu-24.04` / `ubuntu-24.04-arm` GitHub runners (a qemu-based action would violate the official-actions-only policy; native ARM runners avoid it entirely).
- *Why:* lowers the floor (user) and standardizes the "not found"/glibc story; manylinux already vendors static OpenSSL/zlib to aid D1.
- *Alt: build on AlmaLinux 9* — floor too high for wider reuse. *Alt: full cross-compile toolchain* — more complexity than QEMU emulation.

### D6 — CI/CD decomposition (all inputs dynamic)
```
frontier-build.yml (call): checkout pinned FRONTIER_REF -> build static fn-fileget
  (+ libpacparser) in manylinux, per-arch matrix -> upload frontier-runtime_<ver>_<arch>
  + .frontier-manifest.json {ref, sha, version, arch, glibc_floor}
client.yml (call, rewritten): per-arch -> download runtime, stage into
  pd-cds-api-bin resource dir -> uv build (api selector + bin + cli) ->
  fresh-venv smoke test (install wheel; resolve fn-fileget; run query w/o URL
  => expect usage/error, not ENOENT) -> upload wheels
release.yml (extended): matrix across arches -> publish wheels+sdist to PyPI
  via twine + scoped `PYPI_API_TOKEN`/`TESTPYPI_API_TOKEN` repo secrets (the
  official-actions-only policy rules out `pypa/gh-action-pypi-publish`);
  keep GitHub Release for the native bundle
```
Upstream pin lives in a repo variable `FRONTIER_REF` (SHA), so bumping never edits workflow logic; the frontier version is read from the Makefile, not hardcoded.

### D7 — Local dev parity (`uv`)
Add `scripts/stage-frontier-client.sh` that runs the **same** manylinux build in Docker/Podman (or `gh run download`s the CI runtime artifact) and drops `fn-fileget`+`libpacparser.so` into the `pd-cds-api-bin` resource dir. Wire it as a `uv run` pre-step / task; document that `uv build` needs staging first. `.gitignore` the staged native files; `__init__.py` anchors stay tracked.

### D8 — Provenance, licensing, security
Publish `.frontier-manifest.json` and attach SLSA provenance/Cosign attestations (perms already granted). Redistribute `COPYING`/`Fermilab-2009.txt` as license files of `pd-cds-api-bin` (and reference in metadata).

## Risks / Trade-offs

- **Static link of OpenSSL/zlib/expat may fail on the exact manylinux layout** → Mitigation: manylinux provides `*.a`; fall back to `-l:libcrypto.a` explicit paths, and keep a Model-A ("also ship `.so`") build as a documented escape hatch.
- **QEMU aarch64 emulation is slow / flaky for C builds** → Mitigation: run the arm64 leg on a native `ubuntu-24.04-arm` runner where available; QEMU as fallback.
- **`--plat-name` mislabeling (claiming manylinux without passing auditwheel)** → Mitigation: run `auditwheel repair`/`show` as a hard gate; never upload a wheel that fails.
- **Anchor indirection (D3) can silently break resource resolution** → Mitigation: smoke test asserts a resolvable, executable `fn-fileget` after a clean install, on every arch.
- **Removing `bin/` is breaking for existing dev checkouts** → Mitigation: staging script + README/`just` target; CI stages automatically.
- **pacparser `dlopen` name mismatch across distros** → Mitigation: pin the soname we bundle (`libpacparser.so.1`) and `$ORIGIN` rpath so the co-located copy wins.

## Migration Plan

1. Land packaging + `bin/` removal + anchor change + `uv_build` artifacts in one coordinated PR (keeps tree green because CI now stages).
2. Add `frontier-build.yml`; rewire `client.yml`; extend `release.yml`; create `FRONTIER_REF` repo variable + `PYPI_API_TOKEN`/`TESTPYPI_API_TOKEN` repo secrets.
3. Cut a release to publish the first multi-arch wheels.
4. **Rollback:** the previous tagged release (committed `bin/`) remains installable from history; re-enable a bundled-binary path by repointing the anchor if the shim approach must be reverted.

## Open Questions

- Exact glibc floor: `manylinux_2_28` (RHEL8) vs a still-lower `2_17` for legacy EL7 — resolvable post-implementation without changing specs.
- Whether to also publish `py3-none-any` sdists for the bin package (source-less) — packaging detail, not behavior.
