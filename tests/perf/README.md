# Perf tests — Locust harness

`locustfile.py` load-tests the conditions query path end-to-end (Locust →
`pd-cds-api` → staged `fn-fileget` → cache proxy → Frontier server → ConDB2).

**Docs (authoritative):** [Performance testing](https://dune.github.io/frontier-condb2/perf/)
— prerequisites, run commands, task layout, retargeting, and reading the
output (source: [`docs/perf.md`](../../docs/perf.md)).
