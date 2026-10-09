# Proposal

## Why

The client spawns a new `fn-fileget` process per query (~2.2 ms spawn + a cold TCP/proxy connection each time; measured during the latency evaluation). The upstream frontier library already ships a ctypes binding (`bin/python/lib/frontier_client.py` / `frontier.py` in the historical vendored copy, upstream `fermitools/frontier` `client/python/`) that keeps `libfrontier_client.so` loaded and channels open across queries. This change captures that "Tier 1" recommendation for a future in-process client.

## What Changes

- Replace the per-query subprocess boundary with an in-process ctypes client holding persistent channels (one per worker/thread; DB-API threadsafety=1).
- Add a file-get method mirroring `fn-fileget`'s wire protocol (`frontier_file:1:DEFAULT`, double-URL-encode) — the SQL/`frontier_request` binding in `frontier.py` is not a drop-in.
- Optionally enable the C library's native client response cache (`clientcachemaxresultsize=NNN` in the connect string; off by default upstream) — supersedes the Python-level "Tier 3c" option.
- Locust integration must run the ctypes calls on a threadpool (gevent cannot preempt C socket I/O).
- Distribution impact: a `.so` (and its system deps) must ship again or be re-linked into a Python extension — interacts with the pd-cds-api-bin packaging model.

## Capabilities

### New Capabilities
- (intended) `frontier-native-session-management`: persistent-channel query execution semantics. To be delta'd when this change is properly planned.

### Modified Capabilities
- (expected) `frontier-client-packaging`: binary payload shape changes if the shared library (vs static fn-fileget) is shipped. To be delta'd at planning.

## Impact

`pd_cds_api` wrapper/state, the locust harness, wheel content of `pd-cds-api-bin`, and the upstream pin (python bindings come from the same repo). Deferred from the latency evaluation (Tier 1) during the `build-frontier-client-from-upstream` work.
