# Tasks

## 1. Core library (`pd-cds-api`)

- [x] 1.1 Add `proxy_config_url: str = "auto"` field to `ApiClientState` (`client/pd-cds-api/src/pd_cds_api/state.py`) with a `field_validator` accepting only `auto`, `none`, or `http://`/`file://` URLs; error message lists accepted forms; Google-style docstring notes the WPAD default and fatal-on-unreachable-PAC semantics.
- [x] 1.2 Conditionally append `(proxyconfigurl=<value>)` to the `-c` connect string in `ApiClientWrapper._invoke` (`client/pd-cds-api/src/pd_cds_api/wrapper.py`) when `proxy_config_url != "none"`, using the token order `(serverurl=…)(proxyconfigurl=…)(proxyurl=…)`.

## 2. CLI (`pd-cds-cli`)

- [x] 2.1 Add global option `--proxy-config-url` (env `FRONTIER_PROXY_CONFIG_URL`, default `None` → state default) to the Typer callback in `client/pd-cds-cli/src/pd_cds_cli/main.py`, following the `--cache-proxy-url` pattern, and add it to the callback docstring's env-var list.
- [x] 2.2 Ensure a validation failure on the new option exits non-zero with the pydantic message and no subprocess call (wrap `ApiClientState(**overrides)` if the existing pattern does not already cover it).
- [x] 2.3 Add a `--proxy-config-url` row to the resolved-options table in `print_verbose` (`client/pd-cds-cli/src/pd_cds_cli/output.py`, per its keep-in-sync comment) and extend `client/pd-cds-cli/tests/test_output.py` accordingly.

## 3. Tests (pytest)

- [x] 3.1 Extend `client/pd-cds-api/tests/test_state.py`: default is `auto`; valid values (`auto`, `none`, `http://host/path`, `file:///etc/proxy.pac`); invalid values (`https://…`, `wpad/wpad.dat`, empty string) raise `ValidationError`.
- [x] 3.2 Extend `client/pd-cds-api/tests/test_wrapper.py`: default argv contains `(serverurl=…)(proxyconfigurl=auto)(proxyurl=…/)`; explicit URL is passed through verbatim; `none` omits the token; update `test_connect_string_carries_server_and_proxy` and other exact-string assertions for the new default.
- [x] 3.3 Extend `client/pd-cds-cli/tests/test_cli.py`: option and `FRONTIER_PROXY_CONFIG_URL` env var reach the connect string, option beats env; `--proxy-config-url none` reproduces the legacy server+proxy-only string; invalid value exits non-zero without invoking the native client; update `TestDefaults` exact-string assertion.
- [x] 3.4 Run `make test` and `make coverage` (85 % gate), adding any branch cases needed for full coverage of the new code paths.

## 4. Quality gates

- [x] 4.1 `make lint` clean (ruff check + format) on changed files.
- [x] 4.2 `uv run --with pyright pyright client/` clean (mirrors `.github/workflows/client.yml`).

## 5. Documentation

- [x] 5.1 `docs/cli.md`: add `--proxy-config-url` row to the global-options table (default `auto` → `http://wpad/wpad.dat`), plus a short caveat covering WPAD-less networks (`none` escape hatch), PAC-over-HTTP trust note, and the fact that PAC results outrank `--cache-proxy-url`.
- [x] 5.2 Regenerate API reference via `make docs-gen` and commit the updated `docs/reference/pd_cds_api.state.md` (and wrapper page if rendered); verify `make docs` builds strict-clean.

## Workflow follow-up

- Mention the new default (`auto`) in the release notes for the next VERSION bump (repo release process).
- Archive this change with the OpenSpec archive workflow after implementation is merged on branch `50-add-frontier-proxy-auto-config`.
