import os
import subprocess

from pd_cdb_lib.conditions import RunConditions
from pd_cdb_lib.state import ClientState


class Client:
    def __init__(
        self, conditions: RunConditions, state: ClientState | None = None
    ) -> None:
        self.conditions: RunConditions = conditions
        self.state: ClientState = state or ClientState()

    def get_data(self) -> subprocess.CompletedProcess[str]:
        env: dict[str, str] = os.environ.copy()
        env["LD_LIBRARY_PATH"] = self.state.ld_library_path
        serverurl = self.state.api_server_url
        proxyurl = self.state.cache_proxy_url
        connect_string = f"-c '(serverurl={serverurl})(proxyurl={proxyurl})'"
        query_string = self._build_query_string()

        api_call_string = (
            f"{self.state.frontier_client_path} {connect_string} {query_string}"
        )

        subprocess.run(
            args=api_call_string,
            env=env,
            capture_output=True,
            check=True,
            shell=True,
            text=True,
        )

        return self._move_data(query_string)

    def _build_query_string(self) -> str:
        folder = self.conditions.folder
        t0 = self.conditions.t0
        t1 = self.conditions.t1
        data_type = self.conditions.data_type
        format = self.state.format
        query_string = f"'get?folder={folder}"

        if t1 is not None:
            query_string += f"&t0={t0}&t1={t1}"
        else:
            query_string += f"&t={t0}"

        if data_type is not None:
            query_string += f"&data_type={data_type}"
        if format is not None:
            query_string += f"&format={format}"

        return f"{query_string}'"

    def _move_data(self, query_string: str) -> subprocess.CompletedProcess[str]:
        data_dir = "pd-cdb-data"
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
            args=f"mkdir -p {data_dir}",
            capture_output=True,
            check=True,
            shell=True,
            text=True,
        )

        return subprocess.run(
            args=f"mv {query_string} {data_dir}/{output_file} \
                   && echo 'Conditions data written to: {output_file}'",
            capture_output=True,
            check=True,
            shell=True,
            text=True,
        )
