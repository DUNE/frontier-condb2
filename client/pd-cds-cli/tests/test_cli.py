"""Tests for the pd-cds CLI: option plumbing, env vars, validation, errors."""

import subprocess

import pytest

from pd_cds_cli.main import app

GET = ["get-data", "pdunesp.run_conditionstest", "--t0", "25034"]
QUERY = "get?folder=pdunesp.run_conditionstest&t=25034.0&format=csv"


def client_call(spy) -> list[str]:
    """Argv of the fn-fileget invocation (first of client->mkdir->mv calls)."""
    return spy.calls[0]


def connect(spy) -> str:
    argv = client_call(spy)
    return argv[argv.index("-c") + 1]


def invoke(runner, args):
    return runner.invoke(app, args)


class TestDefaults:
    def test_point_query_with_documented_defaults(self, runner, spy) -> None:
        result = invoke(runner, GET)
        assert result.exit_code == 0, result.output
        argv = client_call(spy)
        assert QUERY in argv
        assert "-r" not in argv and "-R" not in argv
        assert connect(spy) == (
            "(serverurl=http://dunefrontier.fnal.gov:8000/dune_runcon_prod)"
            "(proxyurl=http://localhost:3128/)"
        )

    def test_moves_result_into_data_dir(self, runner, spy) -> None:
        invoke(runner, GET)
        assert spy.calls[2][0] == "mv"
        assert spy.calls[2][2].startswith(
            "pd-cds-data/pdunesp.run_conditionstest-t_25034"
        )


class TestGlobalOptions:
    def test_server_url_override_reaches_connect_string(self, runner, spy) -> None:
        invoke(
            runner,
            [
                "--api-server-url",
                "http://fermicloud725.fnal.gov:8000/dune_runcon_prod",
                *GET,
            ],
        )
        assert connect(spy).startswith(
            "(serverurl=http://fermicloud725.fnal.gov:8000/dune_runcon_prod)"
        )

    def test_proxy_url_override_reaches_connect_string(self, runner, spy) -> None:
        invoke(runner, ["--cache-proxy-url", "http://proxy.example:3128", *GET])
        assert "(proxyurl=http://proxy.example:3128/)" in connect(spy)

    @pytest.mark.parametrize(
        ("ttl", "expected"), [("1", "-r"), ("3", "-R")], ids=["short", "forever"]
    )
    def test_ttl_flag_reaches_argv(self, runner, spy, ttl, expected) -> None:
        invoke(runner, ["--ttl", ttl, *GET])
        assert expected in client_call(spy)

    @pytest.mark.parametrize(
        "ttl", ["0", "4", "99"], ids=["below", "above", "way-above"]
    )
    def test_ttl_out_of_range_exits_two(self, runner, spy, ttl) -> None:
        result = invoke(runner, ["--ttl", ttl, *GET])
        assert result.exit_code == 2
        assert spy.calls == []


class TestEnvironmentVariables:
    def test_server_env_var(self, runner, spy, monkeypatch) -> None:
        monkeypatch.setenv("CONDB_API_SERVER_URL", "http://env.example:8000/db")
        invoke(runner, GET)
        assert connect(spy).startswith("(serverurl=http://env.example:8000/db)")

    def test_proxy_env_var(self, runner, spy, monkeypatch) -> None:
        monkeypatch.setenv("FRONTIER_CACHE_PROXY_URL", "http://envproxy.example:3128")
        invoke(runner, GET)
        assert "(proxyurl=http://envproxy.example:3128/)" in connect(spy)

    def test_ttl_env_var(self, runner, spy, monkeypatch) -> None:
        monkeypatch.setenv("FRONTIER_TTL", "3")
        invoke(runner, GET)
        assert "-R" in client_call(spy)

    def test_flag_beats_env_var(self, runner, spy, monkeypatch) -> None:
        monkeypatch.setenv("FRONTIER_TTL", "3")
        invoke(runner, ["--ttl", "1", *GET])
        argv = client_call(spy)
        assert "-r" in argv and "-R" not in argv


class TestCommandOptions:
    def test_range_and_json_and_data_type(self, runner, spy) -> None:
        invoke(
            runner,
            ["get-data", "a.b", "--t0", "1", "--t1", "9", "--dt", "gain", "-f", "json"],
        )
        assert "get?folder=a.b&t0=1.0&t1=9.0&data_type=gain&format=json" in client_call(
            spy
        )


class TestVerbose:
    def test_v_before_subcommand_renders_option_panel(self, runner, spy) -> None:
        result = invoke(runner, ["-v", *GET])
        assert result.exit_code == 0, result.output
        assert "CLI Options" in result.output
        assert "--ttl" in result.output
        assert "Conditions data written to:" in result.output


class TestErrorHandling:
    def test_client_failure_exits_cleanly(self, runner, spy) -> None:
        spy.side_effect = subprocess.CalledProcessError(
            2, ["fn-fileget"], stderr="network error on connect"
        )
        result = invoke(runner, GET)
        assert result.exit_code == 2
        assert "network error on connect" in result.output
        assert "Traceback" not in result.output
