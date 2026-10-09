"""Query execution: invoke the native Frontier client as a subprocess.

:class:`ApiClientWrapper` turns a :class:`~pd_cds_api.conditions.RunConditions`
plus an :class:`~pd_cds_api.state.ApiClientState` into one ``fn-fileget``
invocation (or one batched invocation for several conditions).
"""

import subprocess
from collections.abc import Sequence
from functools import cached_property

from pd_cds_api.conditions import RunConditions
from pd_cds_api.state import ApiClientState

_TTL_FLAGS: dict[int, tuple[str, ...]] = {1: ("-r",), 2: (), 3: ("-R",)}


class ApiClientWrapper:
    """Executes conditions queries through the bundled native client.

    Each public method spawns a single ``fn-fileget`` process with an argv
    list (no shell involved). The wrapper itself is cheap: construct one per
    query (or per batch) and share an
    :class:`~pd_cds_api.state.ApiClientState` freely across instances.
    """

    def __init__(
        self, conditions: RunConditions, state: ApiClientState | None = None
    ) -> None:
        """Bind query parameters and configuration (see the class docstring)."""
        self.conditions: RunConditions = conditions
        self.state: ApiClientState = state or ApiClientState()

    def run_query(self) -> subprocess.CompletedProcess[str]:
        """Fetch this wrapper's conditions with one native-client call.

        Returns:
            The raw :class:`subprocess.CompletedProcess` of ``fn-fileget``.
            Its stdout reports the payload byte count; the CSV/JSON payload
            itself is written by the native client into the current working
            directory under a file named after the query string
            (``get?folder=...``). Use :meth:`get_data` to fetch and relocate
            that file in one step.

        Raises:
            FileNotFoundError: The native runtime is not installed/staged
                (see :attr:`~pd_cds_api.state.ApiClientState.frontier_client_path`).
            subprocess.CalledProcessError: The client exited non-zero
                (server/proxy unreachable, malformed query, etc.).

        Example:
            from pd_cds_api import ApiClientWrapper, RunConditions

            wrapper = ApiClientWrapper(
                conditions=RunConditions(folder="pdunesp.run_conditionstest", t0=25034)
            )
            print(wrapper.run_query().stdout)
        """
        return self._invoke(self.state, [self._query_string])

    @classmethod
    def run_queries(
        cls,
        conditions: Sequence[RunConditions],
        state: ApiClientState | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Fetch several conditions in one native-client process.

        All queries share one process, one connection, and the TTL configured
        on ``state``; the native client stops at the first failed query, so a
        non-zero exit can mean partial success (earlier payloads are already
        on disk).

        Args:
            conditions: Queries to execute, in order.
            state: Shared configuration; defaults to ``ApiClientState()``.

        Returns:
            The combined :class:`subprocess.CompletedProcess`; its stdout has
            one ``"N bytes written to ..."`` line per completed query.

        Raises:
            FileNotFoundError: The native runtime is not installed/staged.
            subprocess.CalledProcessError: Any query failed (see
                :attr:`CompletedProcess.stdout` for those that succeeded).
        """
        state = state or ApiClientState()
        queries = [cls._build_query(c, state) for c in conditions]
        return cls._invoke(state, queries)

    def get_data(self) -> subprocess.CompletedProcess[str]:
        """Fetch and store this wrapper's conditions under ``pd-cds-data/``.

        Performs :meth:`run_query`, then moves the payload file the native
        client wrote into the current working directory to
        ``pd-cds-data/<folder>-t_<t0>.<format>`` (or
        ``...-t0_<t0>-t1_<t1>.<format>`` for range queries).

        Returns:
            The :class:`subprocess.CompletedProcess` of the move step, with
            stdout set to ``"Conditions data written to: <file>"``.

        Raises:
            FileNotFoundError: The native runtime is not installed/staged.
            subprocess.CalledProcessError: The fetch or the move failed.
        """
        self.run_query()
        return self._move_data(self._query_string)

    @staticmethod
    def _invoke(
        state: ApiClientState, queries: Sequence[str]
    ) -> subprocess.CompletedProcess[str]:
        args: list[str] = [
            str(state.frontier_client_path),
            *_TTL_FLAGS[state.frontier_ttl],
            "-c",
            f"(serverurl={state.api_server_url})(proxyurl={state.cache_proxy_url})",
            *queries,
        ]

        return subprocess.run(
            args=args,
            capture_output=True,
            check=True,
            shell=False,
            text=True,
        )

    @cached_property
    def _query_string(self) -> str:
        return self._build_query(self.conditions, self.state)

    @staticmethod
    def _build_query(conditions: RunConditions, state: ApiClientState) -> str:
        query_string = f"get?folder={conditions.folder}"

        if conditions.t1 is not None:
            query_string += f"&t0={conditions.t0}&t1={conditions.t1}"
        else:
            query_string += f"&t={conditions.t0}"

        if conditions.data_type is not None:
            query_string += f"&data_type={conditions.data_type}"
        if state.format is not None:
            query_string += f"&format={state.format}"

        return query_string

    def _move_data(self, query_string: str) -> subprocess.CompletedProcess[str]:
        data_dir = "pd-cds-data"
        folder = self.conditions.folder
        format = self.state.format
        t0 = self.conditions.t0
        t1 = self.conditions.t1
        output_file = f"{folder}-"

        if t1 is not None:
            output_file += f"t0_{t0}-t1_{t1}"
        else:
            output_file += f"t_{t0}"

        output_file += f".{format}"

        subprocess.run(
            args=["mkdir", "-p", data_dir],
            capture_output=True,
            check=True,
            shell=False,
            text=True,
        )

        result = subprocess.run(
            args=["mv", query_string, f"{data_dir}/{output_file}"],
            capture_output=True,
            check=True,
            shell=False,
            text=True,
        )
        result.stdout = f"Conditions data written to: {output_file}\n"
        return result
