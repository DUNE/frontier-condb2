# Proposal

## Why

Two pre-existing API/CLI surface quirks were discovered and deliberately pinned (not changed) by the unit-test suite:

1. The CLI types `--t0/--t1` as `float`, so queries render `t=25034.0` on the wire and in output filenames (`pdunesp.run_conditionstest-t_25034.0.csv`), while direct API use with ints yields clean `t=25034`.
2. `ApiClientWrapper.get_data()` names the output file with `f".{format}"`, so an `ApiClientState(format=None)` produces `…-t_1.None` (test `test_range_query_file_naming` documents the oddity).

## What Changes

- Decide timestamp typing: `RunConditions.t0/t1` stay `int | float`, but CLI should accept/emit ints when whole (e.g., `int | float` typer param or post-parse normalization; wire form `t=25034` preferred for readability/cache-key stability).
- `get_data` filename: fall back to a sane extension when `format is None` (e.g., `.dat`) instead of `.None`.
- Both are observable-behavior changes → update the pinning tests intentionally in the same change, and call out any scripts depending on current filenames.

## Capabilities

### New Capabilities
- (none — modifies conditions/query behavior)

### Modified Capabilities
- (intended, at planning) `frontier-client-packaging` is unaffected; a conditions/query behavior capability does not exist in main specs yet — planning should first capture current `RunConditions`/CLI query semantics as a baseline spec, then delta it.

## Impact

`pd_cds_cli/main.py` option types, `wrapper._build_query`/`_move_data`, CLI + wrapper tests, cache-key stability if caching is later added (coordinate with `add-client-response-caching` — key normalization wants canonical timestamps). Source: unit-test design phase notes ("existing behavior; candidate future change: fallback dat").
