import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from typing import Any

from locust import User, task
from pd_cds_api.conditions import RunConditions
from pd_cds_api.state import ApiClientState
from pd_cds_api.wrapper import ApiClientWrapper

STATE = ApiClientState(format=None, frontier_ttl=3)
FOLDER = "pdunesp.run_conditionstest"


class ApiClient:
    def __init__(self, request_event, state: ApiClientState) -> None:
        self._request_event = request_event
        self._state = state

    def run_query(self, conditions: RunConditions) -> str | None:
        return self._timed_request(
            name=self._request_name(conditions),
            call=lambda: ApiClientWrapper(
                conditions=conditions, state=self._state
            ).run_query(),
        )

    def run_queries(self, conditions: Sequence[RunConditions]) -> str | None:
        names = ", ".join(self._request_name(c) for c in conditions)
        return self._timed_request(
            name=f"batch[{len(conditions)}] {names}",
            call=lambda: ApiClientWrapper.run_queries(conditions, state=self._state),
        )

    def _timed_request(
        self, name: str, call: Callable[[], subprocess.CompletedProcess[str]]
    ) -> str | None:
        _request_meta: dict[str, Any] = {
            "request_type": "fn-fileget",
            "name": name,
            "start_time": time.time(),
            "response_length": 0,
            "response": None,
            "context": {},
            "exception": None,
        }
        _response = None
        _start_perf_counter = time.perf_counter()

        try:
            _response = call().stdout

            if not _response:
                _request_meta["exception"] = "No content in the response."
                sys.stdout.write(
                    f"request_meta['exception']: {_request_meta['exception']}\n"
                )
            else:
                _request_meta["response"] = _response
                _request_meta["response_length"] = len(_response)
                sys.stdout.write(f"request_meta['response']: {_response}\n")
        except subprocess.CalledProcessError as cpe:
            sys.stdout.write(
                f"Subprocess call returned a non-zero value: {cpe.returncode}\n{cpe.stderr}\n{cpe}"
            )
            _request_meta["exception"] = cpe

        _request_meta["response_time"] = (
            time.perf_counter() - _start_perf_counter
        ) * 1000
        self._request_event.fire(**_request_meta)
        return _response

    def _request_name(self, conditions: RunConditions) -> str:
        if conditions.t1 is not None:
            return f"{conditions.folder} t0={conditions.t0} t1={conditions.t1}"
        return f"{conditions.folder} t={conditions.t0}"


class ApiConditionsUser(User):
    abstract = True

    def __init__(self, environment) -> None:
        super().__init__(environment)
        self.client = ApiClient(request_event=environment.events.request, state=STATE)


class ConditionsDataUser(ApiConditionsUser):
    @task
    def pd_vd_run_conditionstest_query(self) -> None:
        self.client.run_query(RunConditions(folder=FOLDER, t0=25034))
        self.client.run_query(RunConditions(folder=FOLDER, t0=25100, t1=25115))
        self.client.run_query(RunConditions(folder=FOLDER, t0=28650, t1=28655))
        self.client.run_query(RunConditions(folder=FOLDER, t0=39252, t1=40260))

    @task
    def pd_vd_run_conditionstest_batch(self) -> None:
        self.client.run_queries(
            [
                RunConditions(folder=FOLDER, t0=25034),
                RunConditions(folder=FOLDER, t0=25100, t1=25115),
                RunConditions(folder=FOLDER, t0=28650, t1=28655),
                RunConditions(folder=FOLDER, t0=39252, t1=40260),
            ]
        )
