"""Tests for the verbose rich renderer."""

import subprocess
from types import SimpleNamespace
from typing import Literal

import pytest
from rich.console import Console

from pd_cds_api.state import ApiClientState
from pd_cds_cli import output as output_module
from pd_cds_cli.output import print_verbose


@pytest.fixture
def recorded_console(monkeypatch: pytest.MonkeyPatch) -> Console:
    console = Console(record=True, width=100, legacy_windows=False)
    monkeypatch.setattr(output_module, "print", console.print)
    return console


def make_ctx(ttl: Literal[1, 2, 3] = 2) -> SimpleNamespace:
    return SimpleNamespace(
        obj=ApiClientState(frontier_ttl=ttl), command_path="pd-cds get-data"
    )


class TestPrintVerbose:
    def test_renders_all_global_option_rows(self, recorded_console: Console) -> None:
        result = subprocess.CompletedProcess(
            args=["fn-fileget"], returncode=0, stdout="42 bytes written", stderr=""
        )
        print_verbose(make_ctx(ttl=3), result)  # type: ignore[arg-type]
        text = recorded_console.export_text()
        for token in ("--api-server-url", "--cache-proxy-url", "--ttl", "--verbose"):
            assert token in text
        assert "42 bytes written" in text

    def test_shows_active_ttl_value(self, recorded_console: Console) -> None:
        result = subprocess.CompletedProcess(
            args=["fn-fileget"], returncode=0, stdout="", stderr=""
        )
        print_verbose(make_ctx(ttl=3), result)  # type: ignore[arg-type]
        assert "3" in recorded_console.export_text()
