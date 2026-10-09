"""Shared fixtures for pd-cds-api tests.

All subprocess execution is faked: nothing in this suite spawns processes or
touches the network.
"""

from collections.abc import Iterator

import pytest
import subprocess
from collections.abc import Sequence

from pd_cds_api import wrapper


class SpyRun:
    """Records ``subprocess.run`` calls; optionally raises."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.kwargs: list[dict] = []
        self.side_effect: Exception | None = None

    def __call__(self, args: Sequence[str], **kwargs) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(args))
        self.kwargs.append(kwargs)
        if self.side_effect is not None:
            raise self.side_effect
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="10 bytes written", stderr=""
        )

    @property
    def last(self) -> list[str]:
        return self.calls[-1]


@pytest.fixture
def spy(monkeypatch: pytest.MonkeyPatch) -> Iterator[SpyRun]:
    """Patch subprocess.run inside the module under test and record calls."""
    recorder = SpyRun()
    monkeypatch.setattr(wrapper.subprocess, "run", recorder)
    yield recorder
