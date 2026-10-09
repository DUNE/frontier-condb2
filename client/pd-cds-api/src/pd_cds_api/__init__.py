"""Public Python API for querying ProtoDUNE run-conditions data.

The package wraps the Frontier client's ``fn-fileget`` executable behind a
small, typed interface:

- :class:`~pd_cds_api.conditions.RunConditions` — what to query (folder and
  time point or interval).
- :class:`~pd_cds_api.state.ApiClientState` — how to connect (server, cache
  proxy, cache TTL, output format).
- :class:`~pd_cds_api.wrapper.ApiClientWrapper` — executes queries by
  invoking the native client as a subprocess.

The native executable is not part of this package: it ships in the companion
``pd_cds_api_bin`` distribution as a self-contained, per-platform wheel
payload and is resolved at runtime through ``importlib.resources``.

Example:
    from pd_cds_api import ApiClientState, ApiClientWrapper, RunConditions

    wrapper = ApiClientWrapper(
        conditions=RunConditions(folder="pdunesp.run_conditionstest", t0=25034),
        state=ApiClientState(),
    )
    result = wrapper.run_query()
"""

from pd_cds_api.conditions import RunConditions
from pd_cds_api.state import ApiClientState
from pd_cds_api.wrapper import ApiClientWrapper

__all__ = ["ApiClientState", "ApiClientWrapper", "RunConditions"]
