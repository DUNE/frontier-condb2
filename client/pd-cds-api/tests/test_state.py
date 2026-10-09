import os

import pytest
from pd_cds_api.state import ApiClientState


def test_frontier_client_path_resolves_executable() -> None:
    path = ApiClientState().frontier_client_path
    assert os.path.isfile(path)
    assert os.access(path, os.X_OK)


def test_missing_native_package_raises_clear_error() -> None:
    with pytest.raises(FileNotFoundError, match="stage-frontier-client"):
        state = ApiClientState(bin_path="pd_cds_api_bin_absent")
        _ = state.frontier_client_path


def test_wrapper_command_construction(monkeypatch) -> None:
    import subprocess

    from pd_cds_api.conditions import RunConditions
    from pd_cds_api.wrapper import ApiClientWrapper

    captured: dict = {}

    def fake_run(*args, **kwargs):
        captured["args"] = args
        captured.update(kwargs)
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    wrapper = ApiClientWrapper(
        conditions=RunConditions(folder="pdunesp.run_conditionstest", t0=1, t1=2)
    )
    wrapper.run_query()

    argv = captured["args"]
    assert argv[0] == str(wrapper.state.frontier_client_path)
    assert "-c" in argv
    assert argv[-1] == "get?folder=pdunesp.run_conditionstest&t0=1&t1=2&format=csv"
    assert "env" not in captured
