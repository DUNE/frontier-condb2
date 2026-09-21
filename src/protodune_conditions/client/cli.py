from subprocess import CompletedProcess
from typing import Annotated, Any

import typer

from protodune_conditions.client.client import Client
from protodune_conditions.client.client_output import print_verbose
from protodune_conditions.client.client_state import ClientState
from protodune_conditions.client.conditions import RunConditions

app = typer.Typer(pretty_exceptions_show_locals=True)


@app.callback()
def main(
    ctx: typer.Context,
    api_server_url: Annotated[
        str | None,
        typer.Option(
            "--api-server-url",
            envvar="CONDB_API_SERVER_URL",
            help=f"(Optional) Conditions Database API Server URL - Default: {ClientState().api_server_url}",
        ),
    ] = None,
    cache_proxy_url: Annotated[
        str | None,
        typer.Option(
            "--cache-proxy-url",
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
    overrides: dict[str, Any] = {}
    overrides["verbose"] = verbose

    if api_server_url is not None:
        overrides["api_server_url"] = api_server_url
    if cache_proxy_url is not None:
        overrides["cache_proxy_url"] = cache_proxy_url

    ctx.obj = ClientState(**overrides)


@app.command()
def get_data(
    ctx: typer.Context,
    folder: Annotated[
        str,
        typer.Argument(
            help="The name of the folder to fetch data from.",
        ),
    ],
    t0: Annotated[
        float,
        typer.Option(
            "--t0",
            help="The beginning of the time interval.",
        ),
    ],
    t1: Annotated[
        float | None,
        typer.Option(
            "--t1",
            help="""
            (Optional) The end of the time interval.
            If specified, the data will be returned for the t0...t1 time interval.
            """,
        ),
    ] = None,
    # tr: Annotated[
    #     float | None,
    #     typer.Option(
    #         "--tr",
    #         help="""
    #         (Optional) Retrieve data retrospectively from a previous state of the database specified with tr as a timestamp.
    #         The result will include only data added before the specified tr.
    #         By default, will include most recent data.
    #         """,
    #     ),
    # ] = None,
    data_type: Annotated[
        str | None,
        typer.Option(
            "--dt",
            help="(Optional) Data type to include. If None, will include data for all data types.",
        ),
    ] = None,
    format: Annotated[
        str | None,
        typer.Option(
            "--format",
            "-f",
            help="(Optional) Format of the output. Can be either 'csv' or 'json' - Default: csv",
        ),
    ] = None,
) -> None:
    if format is not None:
        ctx.obj.format = format

    conditions = RunConditions(folder=folder, t0=t0)
    if t1 is not None:
        conditions.t1 = t1
    # if tr is not None:
    #     conditions.tr = tr
    if data_type is not None:
        conditions.data_type = data_type

    result: CompletedProcess[str] = Client(
        conditions=conditions, state=ctx.obj
    ).get_data()

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise typer.Exit(code=result.returncode)

    if ctx.obj.verbose is True:
        print_verbose(ctx, result)
