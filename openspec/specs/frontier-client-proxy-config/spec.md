# frontier-client-proxy-config Specification

## Purpose

Governs how the Python client library and `pd-cds` CLI configure proxy selection — Proxy Auto-Config (PAC) URL and explicit cache proxy — for the native Frontier client they invoke.

## Requirements

### Requirement: Proxy auto-config is used by default

The client library SHALL default its proxy configuration URL to the Frontier client's `auto` value (which resolves to `http://wpad/wpad.dat`) and SHALL pass it to the native client in the connection string of every query invocation.

#### Scenario: Default state carries auto

- **WHEN** an `ApiClientState` is constructed with no arguments
- **THEN** its `proxy_config_url` equals `auto`

#### Scenario: Default invocation requests WPAD discovery

- **WHEN** a query is executed with default state
- **THEN** the native client's `-c` connection string contains `(proxyconfigurl=auto)`

### Requirement: Proxy configuration URL is user-configurable end to end

The CLI SHALL offer a global `--proxy-config-url` option, readable also from the `FRONTIER_PROXY_CONFIG_URL` environment variable, whose value SHALL propagate through the client library state into the native client connection string.

#### Scenario: CLI option reaches the connection string

- **WHEN** the user runs `pd-cds --proxy-config-url http://wlcg-wpad.fnal.gov/wpad.dat get-data ...`
- **THEN** the connection string contains `(proxyconfigurl=http://wlcg-wpad.fnal.gov/wpad.dat)`

#### Scenario: Environment variable is honored

- **WHEN** `FRONTIER_PROXY_CONFIG_URL` is set and the option is omitted
- **THEN** the env value is used, and an explicit command-line option takes precedence over the environment variable

### Requirement: Proxy auto-config can be disabled

The value `none` SHALL disable proxy auto-configuration: the connection string SHALL omit any `proxyconfigurl` entry, leaving the explicitly configured cache proxy as the only proxy, matching pre-existing behavior.

#### Scenario: Sentinel omits the keyword

- **WHEN** `proxy_config_url` is `none` and a query is executed
- **THEN** the connection string contains no `proxyconfigurl` token

#### Scenario: Disable via CLI

- **WHEN** the user runs `pd-cds --proxy-config-url none get-data ...`
- **THEN** the native client is invoked with today's server-and-proxy-only connection string

### Requirement: Invalid proxy configuration URLs are rejected early

The client library SHALL reject, at state construction time, any `proxy_config_url` that is not `auto`, `none`, or a URL beginning with `http://` or `file://`, because the native client only accepts those forms.

#### Scenario: Unsupported scheme rejected

- **WHEN** `ApiClientState(proxy_config_url="https://example.org/wpad.dat")` is constructed
- **THEN** validation fails with an error naming the accepted forms and the native client is never invoked

#### Scenario: CLI reports invalid value

- **WHEN** the user passes `--proxy-config-url not-a-url`
- **THEN** the CLI exits non-zero with a validation message before any network activity

### Requirement: Explicit cache proxy remains available alongside PAC

When proxy auto-config is active, the client library SHALL still include the configured `cache_proxy_url` as a `proxyurl` entry in the connection string; the native client treats PAC-derived proxies as higher priority and demotes `proxyurl` entries to backup.

#### Scenario: Both tokens present under default

- **WHEN** a query is executed with default state
- **THEN** the connection string contains both `(proxyconfigurl=auto)` and the `(proxyurl=...)` entry for the configured cache proxy
