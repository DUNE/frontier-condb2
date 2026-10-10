# pd-cds-api-bin

Prebuilt native Frontier client runtime shipped to `pd-cds-api`:
self-contained `fn-fileget`, `libpacparser.so.1`, and the
`frontier-manifest.json` provenance record, as per-arch `manylinux_2_28`
wheels. The binaries are **never committed** — built by
`scripts/build-frontier-client.sh` from the pinned `FRONTIER_REF` and staged
by `scripts/stage-frontier-client.sh` (locally) or CI.

**Docs (authoritative):** [what the native wheel ships / install](https://dune.github.io/frontier-condb2/installation/#what-the-native-wheel-ships)
· [releases & `FRONTIER_REF` bumps](https://dune.github.io/frontier-condb2/releases/)
