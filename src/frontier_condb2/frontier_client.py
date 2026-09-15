import os
import subprocess
from collections.abc import Generator
from contextlib import contextmanager
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any


def _bin_path() -> str:
    return "frontier_condb2.bin"


def _client_name() -> str:
    return "fn-fileget"


@contextmanager
def client_path() -> Generator[Path, Any]:
    _resource = files(_bin_path()).joinpath(_client_name())

    with as_file(_resource) as path:
        if not os.access(path, os.X_OK):
            path.chmod(0o755)  # defensive: some install paths lose exec bit
        yield path


def run(connect_string: str) -> subprocess.CompletedProcess:
    with client_path() as exe:
        _env = os.environ.copy()
        _env["LD_LIBRARY_PATH"] = str(files(_bin_path()))

        return subprocess.run(
            f"{exe} {connect_string}",
            env=_env,
            capture_output=True,
            check=True,
            shell=True,
            text=True,
        )
