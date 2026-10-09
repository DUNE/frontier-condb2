"""Tests for ApiClientWrapper: command construction, batching, file handling."""

import subprocess

import pytest

from pd_cds_api.conditions import RunConditions
from pd_cds_api.state import ApiClientState
from pd_cds_api.wrapper import ApiClientWrapper


def make_wrapper(
    state: ApiClientState | None = None, **condition_kwargs
) -> ApiClientWrapper:
    return ApiClientWrapper(
        conditions=RunConditions(folder="pdunesp.run_conditionstest", **condition_kwargs),
        state=state,
    )


class TestQueryConstruction:
    @pytest.mark.parametrize(
        ("condition_kwargs", "state_kwargs", "expected"),
        [
            ({"t0": 25034}, {}, "get?folder=pdunesp.run_conditionstest&t=25034&format=csv"),
            ({"t0": 1, "t1": 9}, {}, "get?folder=pdunesp.run_conditionstest&t0=1&t1=9&format=csv"),
            ({"t0": 1}, {"format": None}, "get?folder=pdunesp.run_conditionstest&t=1"),
            ({"t0": 1}, {"format": "json"}, "get?folder=pdunesp.run_conditionstest&t=1&format=json"),
            (
                {"t0": 1, "data_type": "gain"},
                {},
                "get?folder=pdunesp.run_conditionstest&t=1&data_type=gain&format=csv",
            ),
        ],
        ids=["point", "range", "format-none", "format-json", "data-type"],
    )
    def test_query_string(self, spy, condition_kwargs, state_kwargs, expected) -> None:
        make_wrapper(state=ApiClientState(**state_kwargs), **condition_kwargs).run_query()
        assert spy.last[-1] == expected

    @pytest.mark.parametrize(
        ("ttl", "expected_flag"),
        [(1, "-r"), (2, None), (3, "-R")],
        ids=["short", "default", "forever"],
    )
    def test_ttl_levels_map_to_native_flags(self, spy, ttl, expected_flag) -> None:
        make_wrapper(state=ApiClientState(frontier_ttl=ttl), t0=1).run_query()
        argv = spy.last
        if expected_flag is None:
            assert "-r" not in argv and "-R" not in argv
        else:
            assert expected_flag in argv

    def test_connect_string_carries_server_and_proxy(self, spy) -> None:
        make_wrapper(t0=1).run_query()
        argv = spy.last
        assert argv[argv.index("-c") + 1] == (
            "(serverurl=http://dunefrontier.fnal.gov:8000/dune_runcon_prod)"
            "(proxyurl=http://localhost:3128/)"
        )

    def test_invoked_without_shell_and_without_env(self, spy) -> None:
        make_wrapper(t0=1).run_query()
        assert spy.kwargs[0]["shell"] is False
        assert spy.kwargs[0]["check"] is True
        assert "env" not in spy.kwargs[0]


class TestRunQueries:
    def test_batches_all_queries_into_one_process(self, spy) -> None:
        state = ApiClientState()
        ApiClientWrapper.run_queries(
            [
                RunConditions(folder="a.b", t0=1),
                RunConditions(folder="a.b", t0=2, t1=3),
            ],
            state=state,
        )
        assert len(spy.calls) == 1
        assert spy.last[-2:] == [
            "get?folder=a.b&t=1&format=csv",
            "get?folder=a.b&t0=2&t1=3&format=csv",
        ]

    def test_defaults_state_when_omitted(self, spy) -> None:
        ApiClientWrapper.run_queries([RunConditions(folder="a.b", t0=1)])
        assert len(spy.calls) == 1


class TestGetData:
    def test_fetch_move_sequence_and_naming(self, spy) -> None:
        make_wrapper(t0=1).get_data()
        assert len(spy.calls) == 3
        assert spy.calls[1] == ["mkdir", "-p", "pd-cds-data"]
        assert spy.calls[2] == [
            "mv",
            "get?folder=pdunesp.run_conditionstest&t=1&format=csv",
            "pd-cds-data/pdunesp.run_conditionstest-t_1.csv",
        ]

    def test_range_query_file_naming(self, spy) -> None:
        make_wrapper(state=ApiClientState(format=None), t0=1, t1=9).get_data()
        assert spy.calls[2][-1] == "pd-cds-data/pdunesp.run_conditionstest-t0_1-t1_9.None"

    def test_stdout_reports_written_file(self, spy) -> None:
        result = make_wrapper(t0=1).get_data()
        assert result.stdout == "Conditions data written to: pdunesp.run_conditionstest-t_1.csv\n"


class TestErrorPropagation:
    def test_run_query_propagates_called_process_error(self, spy) -> None:
        spy.side_effect = subprocess.CalledProcessError(2, ["fn-fileget"], stderr="down")
        with pytest.raises(subprocess.CalledProcessError):
            make_wrapper(t0=1).run_query()

    def test_get_data_propagates_before_move(self, spy) -> None:
        spy.side_effect = subprocess.CalledProcessError(2, ["fn-fileget"], stderr="down")
        with pytest.raises(subprocess.CalledProcessError):
            make_wrapper(t0=1).get_data()
        assert len(spy.calls) == 1  # aborted at the fetch, before mkdir/mv
