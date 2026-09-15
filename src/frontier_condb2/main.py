from dataclasses import dataclass
from typing import Annotated

import typer

from frontier_condb2.frontier_client import run

app = typer.Typer()


@dataclass
class ClientState:
    api_server_url: str
    cache_proxy_url: str
    verbose: bool


@app.callback()
def main(
    ctx: typer.Context,
    api_server_url: Annotated[
        str,
        typer.Option(
            "--api-server-url",
            envvar="CDB_API_SERVER_URL",
            help="Conditions Database API Server URL.",
        ),
    ] = "http://dunefrontier.fnal.gov:8000/dune_runcon_prod",
    cache_proxy_url: Annotated[
        str,
        typer.Option(
            "--cache-proxy-url",
            envvar="FRONTIER_CACHE_PROXY_URL",
            help="Frontier Cache Proxy URL.",
        ),
    ] = "http://localhost:3128",
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Turn on verbose output.",
        ),
    ] = False,
) -> None:
    typer.echo(f"Cache Proxy URL: {cache_proxy_url}")
    typer.echo(f"Conditions DB API Server URL: {api_server_url}")

    ctx.obj = ClientState(
        api_server_url=api_server_url, cache_proxy_url=cache_proxy_url, verbose=verbose
    )


@app.command()
def get(ctx: typer.Context) -> None:
    state: ClientState = ctx.obj
    connect_string = (
        f"-c '(serverurl={state.api_server_url})(proxyurl={state.cache_proxy_url})' \
                        'get?folder=pdunesp.run_conditionstest&t0=25100&t1=25115'"
    )
    result = run(connect_string)

    if result.returncode != 0:
        typer.echo(result.stdout)
        typer.echo(result.stderr, err=True)
        raise typer.Exit(code=result.returncode)

    typer.echo(result.stdout)
