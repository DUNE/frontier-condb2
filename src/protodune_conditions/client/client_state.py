import os
from importlib.resources import as_file, files
from pathlib import Path

from pydantic import BaseModel, Field, HttpUrl, computed_field


class ClientState(BaseModel):
    api_server_url: HttpUrl = Field(
        default=HttpUrl("http://dunefrontier.fnal.gov:8000/dune_runcon_prod"),
        validate_default=True,
    )
    bin_path: str = Field(default="protodune_conditions.client.bin", frozen=True)
    cache_proxy_url: HttpUrl = Field(
        default=HttpUrl("http://localhost:3128"),
        validate_default=True,
    )
    frontier_client_name: str = Field(default="fn-fileget", frozen=True)
    verbose: bool = False

    @computed_field
    @property
    def frontier_client_path(self) -> Path:
        resource = files(self.bin_path).joinpath(self.frontier_client_name)

        with as_file(resource) as path:
            if not os.access(path, os.X_OK):
                path.chmod(0o755)  # defensive: some install paths lose exec bit
            return path

    @computed_field
    @property
    def ld_library_path(self) -> str:
        return str(files(self.bin_path))
