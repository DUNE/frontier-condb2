# Design

## Context

See proposal.md for motivation. Research facts from zensical.org (reviewed 2026-10-09, tool at 0.0.69):

- Zensical (by the Material for MkDocs authors, Rust+Python) has **no `gh-deploy` command** — the CLI is `new` / `build` / `serve`. Its documented GitHub Pages path is the official `actions/configure-pages` + `upload-pages-artifact` + `deploy-pages` workflow, which matches the Pages source the user enabled ("GitHub Actions"). **Every deploy replaces the entire site** — hence one deployer.
- Config is a single `zensical.toml` under a `[project]` scope: `site_name`, `site_url`, `docs_dir` (may not be `.`; subdirectory required), `site_dir` (default `site`), `nav`, `watch`, plugins.
- Autodoc: native, behavior-preserving rewrites of MkDocs plugins — `mkdocstrings` (needs the separate `mkdocstrings-python` handler package), `api-autonav`/`autoapi` (module-page generators), `autorefs`, `redirects`, `search` (on by default), `exclude`, `minify`, `llmstxt`. `gen-files` is unsupported; the documented pattern is a generation script run outside the build, with outputs tracked in version control.
- **Implementation-verified (2026-10-09):** Zensical 0.0.69's native mkdocstrings does not cascade `members` into classes rendered through a module-level directive, so pydantic `Field(description=…)` metadata only appears when a directive targets the class itself (`::: pkg.mod.Class` + `members: true`). Griffe extensions (e.g. `griffe-pydantic`) are not honored (`mkdocstrings.handlers.python.extensions` silently ignored). `api-autonav`/`autoapi` emit module-level directives only → unusable for this project's Field-docs substrate.
- `zensical build --strict` fails on warnings/broken links; `--clean` clears the build cache (Zensical recommends clean builds on CI, no caching yet).
- Install as project dev dependency is the recommended pattern (`uv add --dev zensical`), run via `uv run zensical`. Known constraint: Zensical does **not** support uv's symlink link-mode for installs.

Repo state: hub README (explicit stopgap banner) + leaf docs — `infra/README.md` (350-line runbook), `tests/perf/README.md`, `client/pd-cds-{api,api-bin,cli}/README.md`; `docs/images/` exists (image-path debt already fixed in-repo); `.gitignore` already excludes `site/`. `distribute-wheels-via-github-pages` (planned and landed alongside; its generator shipped in `58baa36`) originally planned a `gh-pages` *branch* partition; that premise died with the Pages-mode choice and is amended there (its D1).

## Goals / Non-Goals

**Goals:**
- One command (`make docs` / `uv run zensical serve`) for a full local preview; hermetic, version-pinned via `uv.lock`.
- API reference rendered from the existing docstrings/`Field(description=…)` with zero per-module hand-written stub pages.
- Docs + wheel index co-deploy atomically from a single workflow; structurally clobber-proof.
- Strict link/warning gate on PRs.

**Non-Goals:**
- Versioned docs (mike-style), blog/tags/RSS, social cards, offline builds; prose rewrites beyond link/layout migration; changing what the wheels index contains.

## Decisions

### D1 — Zensical over MkDocs Material
User directive (issue #31); the stub's MkDocs Material assumption is superseded. Material would keep `mkdocstrings` as a third-party plugin; Zensical ships native rewrites and the same theme lineage. Config format: `zensical.toml` (not `mkdocs.yml`) — TOML fits the uv/pyproject-centric repo, and `zensical new` scaffolds it (task 1.2 seeds from that template, then customizes; drop any scaffolder extras we don't use).

### D2 — uv-managed toolchain
`[dependency-groups] docs = ["zensical>=0.0.69", "mkdocstrings-python>=1.x"]` in root `pyproject.toml`; pinned in `uv.lock`; every invocation is `uv run --group docs zensical …` (local via `make docs`, `make docs-serve`; CI via `uv sync --frozen --group docs` which also installs the workspace packages so mkdocstrings can import `pd_cds_api`/`pd_cds_cli`). Org "official `actions/*` only" holds: CI bootstraps uv with a `pip install uv` run-step after `actions/setup-python` (official), never a third-party setup-uv action. Export `UV_LINK_MODE=copy` in the workflow (Zensical + symlink-mode incompatibility). Pin discipline: pre-0.1 tool — upgrades are an explicit, tested `uv lock --upgrade-package zensical` change, never floating.
- *Alt:* `uvx zensical` / `uv tool install` — unpinned drift, and the API handler must import the workspace, which needs the project venv anyway; rejected.

### D3 — Single composed Pages deployer (`pages.yml`); clobber-proof by construction
Actions-mode `deploy-pages` replaces the whole site per run, so exactly one workflow may deploy. `pages.yml` job `deploy`: checkout → setup-python (repo's 3.14) → uv sync (D2) → `zensical build --strict --clean` → `uv run python scripts/build_simple_index.py --from-releases --site-out site/simple` (wheels-change generator, GITHUB_TOKEN env) → guard (D4) → `upload-pages-artifact` (path `site`) → `deploy-pages` (official actions only). `permissions: contents: read, pages: write, id-token: write`; `concurrency: group: pages, cancel-in-progress: false` (serializes overlapping deploys; last run publishes latest main).
Triggers: `push: main` **paths-filtered** to docs-relevant inputs (`docs/**`, `zensical.toml`, `client/**`, `scripts/build_simple_index.py`, `pyproject.toml`, `uv.lock`, the workflow itself); `workflow_run: release.yml completed` (success only) — the index-refresh edge; `workflow_dispatch` (repair/redeploy). `release: published` was rejected as trigger: fires before `release.yml` finishes attaching per-file assets (D4 there), racing the `--from-releases` enumeration; `workflow_run` on completion cannot race.
- *Alt:* `gh-pages` branch as storage + per-producer git-push (keeps wheels-change D1/D5 intact, incremental digests from local wheels) — hidden state, push/deploy double-races, two workflows publishing different snapshots; rejected. *Alt:* switch Pages back to branch source — contradicts the user's enabled mode and Zensical's documented workflow; rejected.

### D4 — Path ownership: docs at site root, `/simple/**` reserved
`site_url = https://DUNE.github.io/frontier-condb2/`; docs own all paths except `/simple/**` (index keeps its wheels-change URL contract; landing page + installation page link it and carry the extra-index instructions from wheels D3). The overlay is ordered docs-build-then-index, so index output always wins for `/simple/**`. Enforced by a CI guard step: fail if `site/simple/` exists before the generator runs (equivalently: `docs/` must never contain `simple/` — cheap `test ! -e` assertion) and if the generator emits anything outside `site/simple`.

### D5 — Content migration (mechanical, stable URLs)
`docs/index.md` (slimmed hub README) · `docs/installation.md` (Pages-index pip/uv/pipx per wheels D3 — the copy-paste source wheels task 4.1 verifies; absorbs the `pd_cds_api_bin` README's native-wheel prose) · `docs/cli.md` (pd-cds-cli README) · `docs/reference/` — **generated & committed** by `scripts/gen_api_reference.py` (stdlib `ast`; amended per the Context limitation): one page per module, class-granularity `mkdocstrings` directives (`members: true` for pydantic field docs), covering `pd_cds_api` + `pd_cds_cli`; `pd_cds_api_bin` excluded (native payload, no API). Drift-guarded by `--check` in CI (build job + deploy job); regenerate via `make docs-gen`. · `docs/infra/runbook.md` (infra/README.md, `docs/images/**` kept, relative links retargeted) · `docs/perf.md` (tests/perf/README.md) · `docs/releases.md` (README "Releases & maintenance" + wheels task 5.3 ownership notes + docs-toolchain maintenance). Leaf READMEs shrink to a pointer block + repo-map table entry so GitHub browsing and the redirect-plugin-free status quo don't break; `redirects` plugin is configured for the few inbound deep links we can't control only if the audit (task 2.6) finds any (none found — all in-site links retargeted in-tree).
- *Alt:* mirror `README.md` into docs pages at build time (mkdocs-monorepo style) — dual source of truth; rejected.

### D6 — PR gate inside `pages.yml`
`build` job (`pull_request`): same steps minus artifact/deploy (strict build + guard + `make lint` unaffected). Deploy job `needs` nothing; push/dispatch runs it standalone. Single workflow file keeps the "only Pages deployer" invariant reviewable in one place.

## Risks / Trade-offs

- **Zensical pre-0.1 (0.0.x), behavior/config churn** → version pinned in `uv.lock`; upgrades are deliberate one-package lock diffs; changelog pinned in docs. Breaking-churn fallback: `mkdocs.yml` compatibility layer eases an exit if ever needed.
- **Every deploy hits the releases API** (`--from-releases` per run, incl. docs-only deploys, since the composed artifact must always contain the index) → cost is O(releases) paginated GETs with GITHUB_TOKEN; trivial at current scale (single-digit releases). If it ever matters: cache the generated `simple/` tree or add incremental mode back (wheels D2 keeps it defined).
- **`workflow_run` token scoping** → runs execute from default-branch code with a fresh token; index refresh after a release therefore reflects *main's* generator script — acceptable (it is the released version), and dispatch remains the repair hatch.
- **Asset-attach ordering** — index correctness now depends on `release.yml` finishing asset attachment before `pages.yml` runs; `workflow_run` on completion encodes exactly that; failed/partial release runs skip deploy (index simply doesn't refresh until next success; rebuild mode is the repair).
- **mkdocstrings imports both client packages at build** → build breaks if a package import breaks; that's a feature (doc CI as smoke test), but it couples docs to runtime-importable state — `pd_cds_api`'s native-runtime resolution is a lazy `ApiClientState` property, verified: the strict build works with no staged binary and no `pd_cds_api_bin` install. CI's sync therefore excludes exactly that one workspace member (`uv sync … --no-install-package pd-cds-api-bin` + `uv run --no-sync`), because its `setup.py` fails any build/editable-install without the staged runtime files — the correct gate for real distributions, wrong for a docs env.
- **committed `docs/reference/` can drift from sources** → `--check` gate in both `pages.yml` jobs (and `make docs` runs `docs-gen` first locally); generator is deterministic (`ast`, source order) so CI diffs stay meaningful.
- **6–9 MB × releases asset hashing in rebuild mode** if the releases API exposes no asset digests → prefer `assets[].digest`; else generator downloads per release (still fine at this scale) — wheels-change task 2.2 owns the fallback.
- **350-line runbook as one page** → acceptable now; split later without URL churn via `redirects` if it grows.

## Migration Plan

1. Land wheels-change generator tasks (2.1–2.3, plus the amended 3.1) so `scripts/build_simple_index.py` exists.
2. Merge this change's docs tree + `pages.yml`; first dispatch deploy publishes docs at `/` and seeds `/simple/**` from existing releases (v0.2.0+) in one atomic site — replaces the wheels plan's separate seeding step.
3. Verify: Pages URLs, strict build green on PRs, install instructions from `docs/installation.md` run verbatim (wheels task 4.1 consumes the page).
4. Rollback: `disable` Pages or revert workflow; index rebuild re-runs anytime (stateless) — no gh-pages branch or other hidden state to unwind.

## Open Questions

- Should `/` eventually host a bare product landing card instead of full docs nav? Default: docs at root now; trivial to layer later with the `redirects` plugin.
- ~~`llmstxt` plugin is free to enable — include `llms.txt` from day one?~~ **Resolved (2026-10-10): no** — not enabled with the initial site; the plugin config needs a `sections` decision that deserves its own small change if wanted.
