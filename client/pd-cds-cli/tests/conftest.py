"""Shared fixtures for pd-cds-cli tests (no subprocesses, no network)."""

import subprocess
from collections.abc import Sequence

import pytest
from typer.testing import CliRunner

from pd_cds_api import wrapper


class SpyRun:
    """Records ``subprocess.run`` calls; optionally raises."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.side_effect: Exception | None = None

    def __call__(
        self, args: Sequence[str], **kwargs
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(args))
        if self.side_effect is not None:
            raise self.side_effect
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="10 bytes written", stderr=""
        )

    @property
    def last(self) -> list[str]:
        return self.calls[-1]


@pytest.fixture
def spy(monkeypatch: pytest.MonkeyPatch) -> SpyRun:
    recorder = SpyRun()
    monkeypatch.setattr(wrapper.subprocess, "run", recorder)
    return recorder


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate tests from option-carrying environment variables on the host."""
    for var in ("CONDB_API_SERVER_URL", "FRONTIER_CACHE_PROXY_URL", "FRONTIER_TTL"):
        monkeypatch.delenv(var, raising=False)
