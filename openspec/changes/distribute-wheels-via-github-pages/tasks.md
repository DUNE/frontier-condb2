# Tasks

## 1. Prerequisites and probes

- [ ] 1.1 (User/Settings) Enable Pages for the repo from branch `gh-pages`, root `/`; verify `https://<org>.github.io/<repo>/` responds.
- [ ] 1.2 Probe that Actions can create+push the `gh-pages` branch with the default token on this org/repo policy (`git init orphan branch; git push origin gh-pages` in a throwaway workflow run or manual run); verify the branch appears and is deletable; record result — fallback per design Risks if blocked.

## 2. Index generator

- [ ] 2.1 Add `scripts/build_simple_index.py` (stdlib-only, PEP 503 normalized names, sha256 fragments, dedupe by href): incremental mode consumes a local `wheels/` dir + tag and an existing `simple/` tree; verify with unit fixtures incl. golden-file HTML assertions under `scripts/tests/` (or `client`-style local test run).
- [ ] 2.2 Add `--from-releases` rebuild mode via GitHub REST (token-authenticated, paginated releases → assets); verify against a fixture API response and that rebuild output equals sequential incremental builds.
- [ ] 2.3 Make the new script pass workspace gates: `make lint` (ruff incl. `D`) green; `python3 scripts/build_simple_index.py --help` works standalone.

## 3. Release workflow distribution

- [ ] 3.1 Add `distribute-python-index` job to `release.yml` per design D5 (push:main + dispatch, `rebuild` input, needs client artifacts, `contents: write`, gh-pages bootstrap, skip-empty commit, single push retry); verify: green run on the branch updates Pages; re-running produces no diff (idempotent) — check via `git diff` on the second run's commit or absence of a new commit.
- [ ] 3.2 Attach unpacked `*.whl` + `*.tar.gz` as release assets in the existing `release` job (`gh release upload --clobber`, fed by an extra unpacked artifact download); verify: v0.2.0 release shows individual wheel files after a run.
- [ ] 3.3 `actionlint` clean; confirm every `uses:` remains official `actions/*`; run `openspec validate` for this change.

## 4. Verification against the live index

- [ ] 4.1 x86_64 AlmaLinux 9: fresh venv, `pip install --extra-index-url <pages>/simple/ pd-cds-cli` → `pd-cds --help` and fn-fileget resolve; `uv` project snippet with `[[tool.uv.index]]` + `explicit = true` resolves `pd-cds*` from Pages and deps from PyPI; `uv tool install` variant; verify commands run exactly as documented (they become the doc text).
- [ ] 4.2 aarch64 selection proof: on an arm64 runner (or `docker run --platform linux/arm64 python:3.14`), `pip download --no-deps --extra-index-url … pd-cds-api-bin` selects `manylinux_2_28_aarch64`; verify filename.
- [ ] 4.3 Negative integrity test: locally edited index page with a wrong `#sha256=` → installer rejects with artifact name (scripted check); verify.
- [ ] 4.4 Token-independence check: with no `PYPI_API_TOKEN`, a release run still updates the Pages index and stays green (or reason from the completed 1.x/3.x runs until a real release occurs; record evidence).

## 5. Documentation

- [ ] 5.1 Root `README.md`: replace/annotate the install path in Quickstart with the Pages index commands (pip/uv/pipx per design D3, including the `--extra-index-url` rationale); keep PyPI wording as "optional, when available".
- [ ] 5.2 `client/pd-cds-cli/README.md` install section updated to the index + direct-URL methods; `client/pd-cds-api/README.md` touched only if it references installation.
- [ ] 5.3 Add a maintenance note to the releases section: index rebuild dispatch (`rebuild=true`), "do not delete releases — index links reference them", Pages path ownership (`/simple/**` reserved for the index; docs tooling gets its own path — cross-link the `adopt-python-docs-tooling` stub).

## Workflow follow-up

- Archive this change once the seeded index passes 4.1–4.2 against real URLs and docs are merged.
- Hand the gh-pages path-partition decision (D1) to the `adopt-python-docs-tooling` change when it is planned.
