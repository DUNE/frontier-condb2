import os
from functools import cache
from importlib.resources import as_file, files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, computed_field

_STAGING_HINT = (
    "Run scripts/stage-frontier-client.sh (local development) or obtain "
    "wheels built by CI."
)


@cache
def _resolve_client_path(bin_path: str, client_name: str) -> Path:
    try:
        resource: Traversable = files(anchor=bin_path).joinpath(client_name)
        with as_file(resource) as path:
            if not os.access(path, mode=os.X_OK):
                path.chmod(mode=0o755)  # defensive: some install paths lose exec bit
            return Path(path)
    except (ModuleNotFoundError, FileNotFoundError) as exc:
        msg = f"Frontier client {client_name!r} not found in package {bin_path!r}. {_STAGING_HINT}"
        raise FileNotFoundError(msg) from exc


class ApiClientState(BaseModel):
    api_server_url: HttpUrl = Field(
        default=HttpUrl(url="http://dunefrontier.fnal.gov:8000/dune_runcon_prod"),
        validate_default=True,
    )
    bin_path: str = Field(default="pd_cds_api_bin", frozen=True)
    cache_proxy_url: HttpUrl = Field(
        default=HttpUrl(url="http://localhost:3128"),
        # default=HttpUrl(url="http://squid.fnal.gov:3128"),
        # default=HttpUrl(url="http://cvmfsbproxy.fnal.gov:3126"),
        validate_default=True,
    )
    format: str | None = "csv"
    frontier_client_name: str = Field(default="fn-fileget", frozen=True)
    frontier_ttl: Literal[1, 2, 3] = 2
    verbose: bool = False

    @computed_field
    @property
    def frontier_client_path(self) -> Path:
        return _resolve_client_path(self.bin_path, self.frontier_client_name)
