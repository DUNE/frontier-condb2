import os
import subprocess

from protodune_conditions.client.client_state import ClientState


class Client:
    def __init__(self, state: ClientState | None = None) -> None:
        self.state = state or ClientState()

    def get_data(self) -> subprocess.CompletedProcess:
        connect_string = f"-c '(serverurl={self.state.api_server_url})(proxyurl={self.state.cache_proxy_url})' \
                          'get?folder=pdunesp.run_conditionstest&t0=28650&t1=28655'"

        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = self.state.ld_library_path

        return subprocess.run(
            f"{self.state.frontier_client_path} {connect_string}",
            env=env,
            capture_output=True,
            check=True,
            shell=True,
            text=True,
        )
