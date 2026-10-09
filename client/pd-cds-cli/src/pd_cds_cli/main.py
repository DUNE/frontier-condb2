"""``pd-cds`` command-line interface.

Defines the Typer application: the callback builds an
:class:`pd_cds_api.ApiClientState` from the global options (each option also
reads a matching environment variable), and the ``get-data`` command fetches
conditions data via :class:`pd_cds_api.ApiClientWrapper`.

Note: parameter help intentionally lives in the ``typer.Option(help=...)``
strings (they embed dynamic defaults); the function docstrings below provide
command summaries/descriptions only, so Typer does not compete with them.
"""

import subprocess
from subprocess import CompletedProcess
from typing import Annotated, Any

import typer
from pd_cds_api.conditions import RunConditions
from pd_cds_api.state import ApiClientState
from pd_cds_api.wrapper import ApiClientWrapper

from pd_cds_cli.output import print_verbose

app = typer.Typer(pretty_exceptions_show_locals=True)


@app.callback()
def main(
    ctx: typer.Context,
    api_server_url: Annotated[
        str | None,
        typer.Option(
            "--api-server-url",
            envvar="CONDB_API_SERVER_URL",
            help=f"(Optional) Conditions Database API Server URL - Default: {ApiClientState().api_server_url}",
        ),
    ] = None,
    cache_proxy_url: Annotated[
        str | None,
        typer.Option(
            "--cache-proxy-url",
            envvar="FRONTIER_CACHE_PROXY_URL",
            help=f"(Optional) Frontier Cache Proxy URL - Default: {ApiClientState().cache_proxy_url}",
        ),
    ] = None,
    ttl: Annotated[
        int | None,
        typer.Option(
            "--ttl",
            min=1,
            max=3,
            envvar="FRONTIER_TTL",
            help=f"(Optional) Frontier cache time-to-live: 1=short, 2=default, 3=forever - Default: {ApiClientState().frontier_ttl}",
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
    """ProtoDUNE Conditions Data Service client.

    Global options must appear before the subcommand. They may also be set
    via environment variables (CONDB_API_SERVER_URL,
    FRONTIER_CACHE_PROXY_URL, FRONTIER_TTL).
    """
    overrides: dict[str, Any] = {}
    overrides["verbose"] = verbose

    if api_server_url is not None:
        overrides["api_server_url"] = api_server_url
    if cache_proxy_url is not None:
        overrides["cache_proxy_url"] = cache_proxy_url
    if ttl is not None:
        overrides["frontier_ttl"] = ttl

    ctx.obj = ApiClientState(**overrides)


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
    """Retrieve run-conditions data for a folder and time point or range.

    The result is written under ./pd-cds-data/ as
    <folder>-t_<t0>.<format> (point query) or
    <folder>-t0_<t0>-t1_<t1>.<format> (range query). A failed native-client
    call prints its error output and exits non-zero.
    """
    if format is not None:
        ctx.obj.format = format

    conditions = RunConditions(folder=folder, t0=t0)
    if t1 is not None:
        conditions.t1 = t1
    # if tr is not None:
    #     conditions.tr = tr
    if data_type is not None:
        conditions.data_type = data_type

    try:
        result: CompletedProcess[str] = ApiClientWrapper(
            conditions=conditions, state=ctx.obj
        ).get_data()
    except subprocess.CalledProcessError as cpe:
        print(cpe.stderr)
        raise typer.Exit(code=cpe.returncode) from None

    if ctx.obj.verbose is True:
        print_verbose(ctx, result)
