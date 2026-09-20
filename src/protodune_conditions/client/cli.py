from subprocess import CompletedProcess
from typing import Annotated

import typer

from protodune_conditions.client.client import Client
from protodune_conditions.client.client_output import verbose
from protodune_conditions.client.client_state import ClientState

app = typer.Typer(pretty_exceptions_show_locals=True)


@app.callback()
def main(
    ctx: typer.Context,
    api_server_url: Annotated[
        str | None,
        typer.Option(
            default="--api-server-url",
            envvar="CONDB_API_SERVER_URL",
            help=f"(Optional) Conditions Database API Server URL - Default: {ClientState().api_server_url}",
        ),
    ] = None,
    cache_proxy_url: Annotated[
        str | None,
        typer.Option(
            default="--cache-proxy-url",
            envvar="FRONTIER_CACHE_PROXY_URL",
            help=f"(Optional) Frontier Cache Proxy URL - Default: {ClientState().cache_proxy_url}",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="(Optional) Turn on verbose output.",
        ),
    ] = False,
) -> None:
    overrides: dict[str, str] = {}
    overrides["verbose"] = str(object=verbose)

    if api_server_url is not None:
        overrides["api_server_url"] = api_server_url
    if cache_proxy_url is not None:
        overrides["cache_proxy_url"] = cache_proxy_url

    ctx.obj = ClientState(**overrides)


@app.command()
def get_data(
    ctx: typer.Context,
    format: Annotated[
        str | None,
        typer.Option(
            default="--format",
            help="(Optional) Format of the output. Can be either 'csv' or 'json' - Default: csv",
        ),
    ] = None,
) -> None:
    overrides: dict[str, str] = {}

    if format is not None:
        overrides["format"] = format
        ctx.obj = ClientState(**overrides)

    result: CompletedProcess[str] = Client(state=ctx.obj).get_data()

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise typer.Exit(code=result.returncode)

    if bool(ctx.obj.verbose) is True:
        verbose(ctx, result)
