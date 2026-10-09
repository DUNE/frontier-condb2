# Perf tests — Locust harness

`locustfile.py` load-tests the conditions query path end-to-end:
[Locust](https://locust.io) users → [`pd-cds-api`](../../client/pd-cds-api/README.md)
`ApiClientWrapper` → staged [`fn-fileget`](../../client/pd-cds-api-bin/README.md)
→ cache proxy → Frontier server → ConDB2. Setup from a fresh clone:
[root README](../../README.md).

## Prerequisites

1. `make stage` (or `scripts/stage-frontier-client.sh --from-ci <run-id>`) —
   the harness shells out to the real native client, so the runtime must be
   staged.
2. FNAL VPN **and** a local Squid cache on `localhost:3128` — build it via the
   [infra runbook: Frontier Squid Cache Setup on a Local Workstation](../../infra/README.md#frontier-squid-cache-setup-on-a-local-workstation).
   Without it every request fails with connection errors (the stats table
   still populates, just with failures).

## Run

```bash
# Web UI at http://localhost:8089 — pick ConditionsDataUser, set users/spawn rate,
# the "host" field is ignored (URLs come from STATE inside the file)
uv run locust -f tests/perf/locustfile.py --processes -1

# Scripted headless run: 50 users, ramp 10/s, 60s
uv run locust -f tests/perf/locustfile.py --processes -1 --headless -u 50 -r 10 -t 60s
```

`--processes -1` runs one worker process per CPU core (the native client is
subprocess-bound, so multi-process scales far better than a single Python
process); a master aggregates one stats table. Use `--processes N` to cap it.

## What it runs

`ConditionsDataUser` picks randomly between two tasks:

| Task | Behavior | Stats rows |
|---|---|---|
| `pd_vd_run_conditionstest_query` | 4 sequential `run_query()` calls against `pdunesp.run_conditionstest` (one point query, three ranges) | 4 events, one per query (`<folder> t=…` / `t0=… t1=…`) |
| `pd_vd_run_conditionstest_batch` | same 4 queries as **one** `run_queries()` batch → one `fn-fileget` process, one connection | 1 event named `batch[4] …` |

Batch vs granular medians in one run directly show the batching win from the
earlier latency work (TTL/`frontier_ttl=3` requests `forever` proxy caching,
so warmed runs should show high `TCP_HIT` rates in the Squid access log).

## Retarget / customize

Edit the module-level constants at the top of `locustfile.py`:

```python
STATE = ApiClientState(format=None, frontier_ttl=3,
                       api_server_url="http://fermicloud725.fnal.gov:8000/dune_runcon_prod",
                       cache_proxy_url="http://localhost:3128")
FOLDER = "pdunesp.run_conditionstest"
```

Add tasks (e.g. `neardet2x2.gain` ranges) by copying an existing method and
building `RunConditions(folder=..., t0=..., t1=...)`.

## Reading the output

- Latency is measured around the subprocess call only (spawn + connect +
  transfer + teardown of `fn-fileget`), excluding Locust scheduling.
- `No content in the response.` in the log = the client ran but returned an
  empty payload (counted as a failure).
- Non-zero exits appear as request failures with the subprocess error output.
