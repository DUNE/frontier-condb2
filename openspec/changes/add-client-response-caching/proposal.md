# Proposal

## Why

Repeated/similar conditions queries pay full network latency even though conditions data is time-versioned and mostly immutable per `(folder, t0, t1)`. The full Tier 3 design was produced during the latency evaluation but deliberately deferred. Note the architecture dependency: under the current per-query-subprocess model, only a **disk** cache survives across queries; in-memory caching becomes effective once the in-process client (see `add-in-process-frontier-client`) lands, and after that the C library's native `clientcachemaxresultsize` may suffice (decision 3c).

## What Changes

- `ResponseCache` protocol in `pd_cds_api` with backends: stdlib TTL-LRU `MemoryCache`, `DiskCache` (XDG cache dir, sha256 keys, atomic writes, TTL on read), `NullCache` default.
- Cache key: `v1|api_server_url|cache_proxy_url|folder|t0|t1|data_type|format`.
- Staleness policy: bounded ranges / historical `t` immutable-on-opt-in; "recent" queries TTL ≤ Frontier server max-cache-age (align with `frontier_ttl`); `refresh` bypass flag.
- Single-flight coalescing per key (thundering-herd control; gevent/thread-safe locks).
- New `ApiClientState` fields (default OFF so the perf harness keeps measuring real calls): `cache_enabled`, `cache_backend`, `cache_dir`, `cache_ttl_seconds`, `cache_max_bytes`.
- `CachingClient` facade (wrapper stays pure); hits/misses/evictions stats; locust gated task with distinct `request_type="cache-hit"`.
- Tests: key stability, TTL expiry (frozen time), single-flight, disk atomicity, bypass.

## Capabilities

### New Capabilities
- (intended) `client-response-caching`: cache-hit/miss/staleness/bypass behavior. To be delta'd at planning.

### Modified Capabilities
- (none expected beyond the new capability; `frontier-client-packaging` untouched)

## Impact

New modules `pd_cds_api/cache.py` / `pd_cds_api/client.py`, state config surface, CLI flags (`--cache/--refresh`, verbose stats), locustfile. Decision from the Tier 3 evaluation remains: consider doing this after Tier 1 (in-process client) so memory caching is meaningful.
