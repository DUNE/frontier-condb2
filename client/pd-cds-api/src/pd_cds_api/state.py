"""Client configuration state for the conditions API.

:class:`ApiClientState` is the single place where connection and payload
preferences live. It is validated (``pydantic``), safe to share across calls,
and exposes the location of the native executable bundled by the companion
``pd_cds_api_bin`` package.
"""

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
    """Connection and payload configuration for one client workflow.

    All fields have production defaults, so ``ApiClientState()`` is always
    usable; the CLI overrides individual fields from its global options and
    matching environment variables. Values are validated at construction time.
    """

    api_server_url: HttpUrl = Field(
        default=HttpUrl(url="http://dunefrontier.fnal.gov:8000/dune_runcon_prod"),
        validate_default=True,
        description="Conditions Database API server URL (Frontier servlet).",
    )
    bin_path: str = Field(
        default="pd_cds_api_bin",
        frozen=True,
        description=(
            "Internal: importlib.resources anchor package holding the native "
            "runtime; not user-configurable."
        ),
    )
    cache_proxy_url: HttpUrl = Field(
        default=HttpUrl(url="http://localhost:3128"),
        # default=HttpUrl(url="http://squid.fnal.gov:3128"),
        # default=HttpUrl(url="http://cvmfsbproxy.fnal.gov:3126"),
        validate_default=True,
        description="Frontier cache proxy used to reach the API server.",
    )
    format: str | None = Field(
        default="csv",
        description=(
            "Response format appended to the query (``csv`` or ``json``); "
            "``None`` omits the parameter entirely."
        ),
    )
    frontier_client_name: str = Field(
        default="fn-fileget",
        frozen=True,
        description="Internal: file name of the native executable; not user-configurable.",
    )
    frontier_ttl: Literal[1, 2, 3] = Field(
        default=2,
        description=(
            "Frontier proxy cache time-to-live level: 1 = short (fresh "
            "fetch), 2 = server default, 3 = forever (immutable historical "
            "data). Higher levels trade freshness for latency."
        ),
    )
    verbose: bool = Field(
        default=False,
        description="Enable verbose output (CLI only; the API ignores it).",
    )

    @computed_field
    @property
    def frontier_client_path(self) -> Path:
        """Absolute filesystem path to the executable ``fn-fileget``.

        Resolved from the ``pd_cds_api_bin`` resource package and cached per
        anchor/name; the exec bit is restored defensively when an installer
        drops it.

        Raises:
            FileNotFoundError: The native runtime is not staged/installed.
                The message names the remediation step (staging script or
                CI-built wheels).
        """
        return _resolve_client_path(self.bin_path, self.frontier_client_name)
