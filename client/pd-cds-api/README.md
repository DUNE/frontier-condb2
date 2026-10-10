# pd-cds-api

ProtoDUNE Conditions Data Service — Python client API. Wraps the Frontier
client's `fn-fileget` to query run-conditions folders by timestamp/time-range;
the native executable ships separately in
[`pd-cds-api-bin`](../pd-cds-api-bin/) and is resolved at runtime via
`importlib.resources`.

**Docs (authoritative):** [API reference](https://dune.github.io/frontier-condb2/reference/pd_cds_api/)
· [installation](https://dune.github.io/frontier-condb2/installation/)
· dev quickstart: [site home](https://dune.github.io/frontier-condb2/#choose-your-path)

Local flow unchanged: `make stage && uv sync`, then `make build / test / smoke`.
