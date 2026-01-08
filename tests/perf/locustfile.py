import os
import subprocess
import time

from locust import User, task


class SubprocessClient:
    def __init__(self, request_event) -> None:
        self._request_event = request_event

    def __getattr__(self, name):
        def wrapper(*args):
            request_meta = {
                "request_type": "subprocess.run()",
                "name": name,
                "start_time": time.time(),
                "response_length": 0,
                "response": None,
                "context": {},
                "exception": None,
            }
            start_perf_counter = time.perf_counter()

            _env = os.environ.copy()
            _env["LD_LIBRARY_PATH"] = "/home/mike/dev/frontier/client"
            print(f"_env['LD_LIBRARY_PATH']: {_env['LD_LIBRARY_PATH']}")
            result = subprocess.run(
                [*args],
                env=_env,
                capture_output=True,
                shell=True,
                text=True,
            )

            print(f"STDOUT: {result.stdout}\n")

            if result.returncode != 0:
                request_meta["exception"] = result.stdout
            else:
                request_meta["response"] = result.stdout

            request_meta["response_time"] = (
                time.perf_counter() - start_perf_counter
            ) * 1000
            self._request_event.fire(**request_meta)
            return request_meta["response"]

        return wrapper


class SubProcessUser(User):
    abstract = True

    def __init__(self, environment) -> None:
        super().__init__(environment)
        self.client = SubprocessClient(request_event=environment.events.request)


class ConditionsDataUser(SubProcessUser):
    # @task
    # def curl_query_cdb(self) -> None:
    #     self.client.curl_query_cdb(
    #         'curl "https://dbdata0vm.fnal.gov:9443/dune_runcon_prod/get?folder=pdunesp.test&t=0"'
    #     )

    @task
    def fnfileget_query_cdb(self) -> None:
        self.client.fnfileget_query_cdb(
            './clients/frontier/client/fn-fileget -c "(serverurl=http://fermicloud725.fnal.gov:8000/dune_runcon_prod)(proxyurl=http://localhost:3128)" "get?folder=pdunesp.run_conditionstest&t0=25100&t1=25115"',
        )
