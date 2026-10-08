import os
import subprocess
from collections.abc import Sequence
from functools import cached_property

from pd_cds_api.conditions import RunConditions
from pd_cds_api.state import ApiClientState

_TTL_FLAGS: dict[int, tuple[str, ...]] = {1: ("-r",), 2: (), 3: ("-R",)}


class ApiClientWrapper:
    def __init__(
        self, conditions: RunConditions, state: ApiClientState | None = None
    ) -> None:
        self.conditions: RunConditions = conditions
        self.state: ApiClientState = state or ApiClientState()

    def run_query(self) -> subprocess.CompletedProcess[str]:
        return self._invoke(self.state, [self._query_string])

    @classmethod
    def run_queries(
        cls,
        conditions: Sequence[RunConditions],
        state: ApiClientState | None = None,
    ) -> subprocess.CompletedProcess[str]:
        state = state or ApiClientState()
        queries = [cls._build_query(c, state) for c in conditions]
        return cls._invoke(state, queries)

    def get_data(self) -> subprocess.CompletedProcess[str]:
        self.run_query()
        return self._move_data(self._query_string)

    @staticmethod
    def _invoke(
        state: ApiClientState, queries: Sequence[str]
    ) -> subprocess.CompletedProcess[str]:
        env: dict[str, str] = os.environ.copy()
        env["LD_LIBRARY_PATH"] = state.ld_library_path

        args: list[str] = [
            str(state.frontier_client_path),
            *_TTL_FLAGS[state.frontier_ttl],
            "-c",
            f"(serverurl={state.api_server_url})(proxyurl={state.cache_proxy_url})",
            *queries,
        ]

        return subprocess.run(
            args=args,
            env=env,
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
