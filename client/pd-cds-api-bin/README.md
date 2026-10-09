# pd-cds-api-bin

Prebuilt native Frontier client runtime shipped to `pd-cds-api`.

This distribution carries the self-contained `fn-fileget` executable,
`libpacparser.so.1` (PAC support, loaded via `dlopen` resolved by the binary's
`$ORIGIN` runpath), and the `frontier-manifest.json` provenance record.

The binary files are **not committed**. They are produced by
`scripts/build-frontier-client.sh` (containerized manylinux_2_28 build from a
pinned `fermitools/frontier` revision) and staged into
`src/pd_cds_api_bin/` by `scripts/stage-frontier-client.sh` (locally) or CI.

Wheels are platform-specific (`cp-free`, `py3-none-manylinux_2_28_<arch>`).
Set `FRONTIER_WHEEL_PLAT` to override the platform tag.

Upstream code is (c) Fermilab under the Fermitools BSD license; see `COPYING`
and `Fermilab-2009.txt`.
