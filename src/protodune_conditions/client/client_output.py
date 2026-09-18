from subprocess import CompletedProcess

import typer
from rich import print
from rich.console import Group
from rich.padding import Padding
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text


def verbose(ctx: typer.Context, result: CompletedProcess) -> None:
    details_panel_title_text = Text(
        f"Command Details: <{ctx.command_path}>", style="bright_magenta"
    )
    results_panel_title_text = Text(
        f"Command Results: <{ctx.command_path}>", style="bright_magenta"
    )
    result_text = Padding(Text(f"{result.stdout}", style="bright_cyan"), (1, 1, 0, 2))

    options_table_title = Text(
        "CLI Options", style=Style(color="bright_yellow", italic=True)
    )
    table = Table(title=options_table_title, style="grey50")
    table.add_column("Option", style="bright_cyan", no_wrap=True)
    table.add_column("Value", style="bright_magenta", no_wrap=True)
    table.add_row("--api-server-url", f"{ctx.obj.api_server_url}")
    table.add_row("--cache-proxy-url", f"{ctx.obj.cache_proxy_url}")
    table.add_row("--verbose, -v", f"{ctx.obj.verbose}")
    padded_table = Padding(table, 1)

    panel_group = Group(
        Panel(padded_table, title=details_panel_title_text),
        Panel(
            result_text,
            title=results_panel_title_text,
        ),
    )

    print()
    print(panel_group)
    print()
