# Proposal

## Why

The OpenSpec design for `build-frontier-client-from-upstream` recorded an explicit open question: whether to lower the wheel baseline from **manylinux_2_28** (RHEL/Alma 8 build base) to **manylinux_2_17** to cover legacy EL7 consumers. Related deferred thought from the same work: builds are provenance-deterministic but not **byte-reproducible** (ELF debug path records differ per build tmpdir), which future verification/audit workflows may want.

## What Changes

- Evaluate manylinux_2_17 (`quay.io/pypa/manylinux_2_17_*`): gcc-toolset/pacparser/OpenSSL-static feasibility on CentOS 7 userland, QEMU-vs-runner constraints (no native EL7-era runners; arm64 under 2_17 policy), and whether any target audience actually needs <2.28 — if not, formally close the question and record the decision.
- If adopted: retag wheels (`FRONTIER_WHEEL_PLAT` already parameterized), auditwheel gate floor, docs/runbook updates.
- Optional sibling hardening: byte-reproducible builds via `-ffile-prefix-map=$work=/build` (frontier + pacparser + our link) and SOURCE_DATE_EPOCH everywhere, verified by two-build digest comparison; document `SOURCE_DATE_EPOCH` as an artifact attestation input.

## Capabilities

### New Capabilities
- (none expected; packaging-target decision)

### Modified Capabilities
- (intended, at planning) `frontier-client-packaging`: wheel-platform targeting requirement may need its baseline restated. To be delta'd only if the floor actually changes.

## Impact

`scripts/build-frontier-client.sh`, `frontier-build.yml` matrix (image + runner strategy), auditwheel gate constant. Source: design.md "Open Questions" + Risks ("ELF bytes may still differ in debug path records") in `build-frontier-client-from-upstream`.
