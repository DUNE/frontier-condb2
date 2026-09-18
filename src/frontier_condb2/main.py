from typing import Annotated

import typer

from frontier_condb2.client import Client
from frontier_condb2.client_output import verbose
from frontier_condb2.client_state import ClientState

app = typer.Typer(pretty_exceptions_show_locals=True)


@app.callback()
def main(
    ctx: typer.Context,
    api_server_url: Annotated[
        str | None,
        typer.Option(
            "--api-server-url",
            envvar="CONDB_API_SERVER_URL",
            help=f"Conditions Database API Server URL - Default: {ClientState().api_server_url}",
        ),
    ] = None,
    cache_proxy_url: Annotated[
        str | None,
        typer.Option(
            "--cache-proxy-url",
            envvar="FRONTIER_CACHE_PROXY_URL",
            help=f"Frontier Cache Proxy URL - Default: {ClientState().cache_proxy_url}",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Turn on verbose output.",
        ),
    ] = False,
) -> None:
    overrides = {}
    overrides["verbose"] = verbose

    if api_server_url is not None:
        overrides["api_server_url"] = api_server_url
    if cache_proxy_url is not None:
        overrides["cache_proxy_url"] = cache_proxy_url

    ctx.obj = ClientState(**overrides)


@app.command()
def get_data(ctx: typer.Context) -> None:
    result = Client(ctx.obj).get_data()

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise typer.Exit(code=result.returncode)

    if ctx.obj.verbose is True:
        verbose(ctx, result)
