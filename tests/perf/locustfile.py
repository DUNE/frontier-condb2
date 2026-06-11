import os
import subprocess
import sys
import time
from typing import Any, Callable

from locust import User, task

CONDB2_SERVER_URL = "https://dbdata0vm.fnal.gov:9443/dune_runcon_prod"
FN_FILEGET_PATH = "./clients/frontier/client/fn-fileget"
FRONTIER_CLIENT_LD_LIBRARY_PATH = "/home/mike/dev/frontier/client"
FRONTIER_PROXY_URL = "http://localhost:3128"
# FRONTIER_SERVER_URL = "http://fermicloud725.fnal.gov:8000/dune_runcon_prod"
FRONTIER_SERVER_URL = "http://dunefrontier.fnal.gov:8000/dune_runcon_prod"


class SubprocessClient:
    def __init__(self, request_event) -> None:
        self._request_event = request_event

    def __getattr__(self, name) -> Callable[..., Any | str]:
        def wrapper(*args) -> Any | str:
            _env = os.environ.copy()
            _env["LD_LIBRARY_PATH"] = FRONTIER_CLIENT_LD_LIBRARY_PATH
            _request_meta = {
                "request_type": f"{args}",
                "name": name,
                "start_time": time.time(),
                "response_length": 0,
                "response": None,
                "context": {},
                "exception": None,
            }
            _result = None
            _start_perf_counter = time.perf_counter()

            try:
                _result = subprocess.run(
                    [*args],
                    env=_env,
                    capture_output=True,
                    check=True,
                    shell=True,
                    text=True,
                )

                if (
                    not _result.stdout
                    or len(_result.stdout) == 0
                    or _result.stdout == ""
                ):
                    _request_meta["exception"] = "No content in the response."
                    sys.stdout.write(
                        f"request_meta['exception']: {_request_meta['exception']}\n"
                    )
                else:
                    _request_meta["response"] = _result.stdout
                    sys.stdout.write(
                        f"request_meta['response']: {_request_meta['response']}\n"
                    )
            except subprocess.CalledProcessError as cpe:
                sys.stdout.write(
                    f"Subprocess call returned a non-zero value: {cpe.returncode}\n{cpe.stderr}\n{cpe}"
                )
                _request_meta["exception"] = cpe

            _request_meta["response_time"] = (
                time.perf_counter() - _start_perf_counter
            ) * 1000
            self._request_event.fire(**_request_meta)
            return _request_meta["response"]

        return wrapper


class SubProcessUser(User):
    abstract = True

    def __init__(self, environment) -> None:
        super().__init__(environment)
        self.client = SubprocessClient(request_event=environment.events.request)


class ConditionsDataUser(SubProcessUser):
    # @task
    # def pd_vd_curl_query(self) -> None:
    #     self.client.curl_query_cdb(
    #         f"curl '{CONDB2_SERVER_URL}/get?folder=pdunesp.run_conditionstest&t=25034'"
    #     )
    #     self.client.curl_query_cdb(
    #         f"curl '{CONDB2_SERVER_URL}/get?folder=pdunesp.run_conditionstest&t0=25100&t1=25115'"
    #     )
    #     self.client.curl_query_cdb(
    #         f"curl '{CONDB2_SERVER_URL}/get?folder=pdunesp.run_conditionstest&t0=28650&t1=28655'"
    #     )
    #     self.client.curl_query_cdb(
    #         f"curl '{CONDB2_SERVER_URL}/get?folder=pdunesp.run_conditionstest&t0=39252&t1=40260'"
    #     )

    @task
    def pd_vd_fnfileget_query(self) -> None:
        self.client.pd_vd_fnfileget_query(
            f"{FN_FILEGET_PATH} -c '(serverurl={FRONTIER_SERVER_URL})(proxyurl={FRONTIER_PROXY_URL})' 'get?folder=pdunesp.run_conditionstest&t=25034'",
        )
        self.client.pd_vd_fnfileget_query(
            f"{FN_FILEGET_PATH} -c '(serverurl={FRONTIER_SERVER_URL})(proxyurl={FRONTIER_PROXY_URL})' 'get?folder=pdunesp.run_conditionstest&t0=25100&t1=25115'",
        )
        self.client.pd_vd_fnfileget_query(
            f"{FN_FILEGET_PATH} -c '(serverurl={FRONTIER_SERVER_URL})(proxyurl={FRONTIER_PROXY_URL})' 'get?folder=pdunesp.run_conditionstest&t0=28650&t1=28655'",
        )
        self.client.pd_vd_fnfileget_query(
            f"{FN_FILEGET_PATH} -c '(serverurl={FRONTIER_SERVER_URL})(proxyurl={FRONTIER_PROXY_URL})' 'get?folder=pdunesp.run_conditionstest&t0=39252&t1=40260'",
        )

    # @task
    # def pd_2x2_fnfileget_query(self) -> None:
    # curl "https://dbdata0vm.fnal.gov:9443/dune_runcon_prod/get?folder=neardet2x2.gain&t=0"
    # curl "https://dbdata0vm.fnal.gov:9443/dune_runcon_prod/get?folder=neardet2x2.elifetime&t=0"
    # curl "https://dbdata0vm.fnal.gov:9443/dune_runcon_prod/get?folder=neardet2x2.vdrift&t=0"
    # self.client.pd_2x2_fnfileget_query(
    #     f"{FN_FILEGET_PATH} -c '(serverurl={FRONTIER_SERVER_URL})(proxyurl={FRONTIER_PROXY_URL})' 'get?folder=neardet2x2.gain&t=0'",
    # )
    # self.client.pd_2x2_fnfileget_query(
    #     f"{FN_FILEGET_PATH} -c '(serverurl={FRONTIER_SERVER_URL})(proxyurl={FRONTIER_PROXY_URL})' 'get?folder=neardet2x2.elifetime&t=0'",
    # )
    # self.client.pd_2x2_fnfileget_query(
    #     f"{FN_FILEGET_PATH} -c '(serverurl={FRONTIER_SERVER_URL})(proxyurl={FRONTIER_PROXY_URL})' 'get?folder=neardet2x2.vdrift&t=0'",
    # )
