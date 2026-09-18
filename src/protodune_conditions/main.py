import typer

import protodune_conditions.client.cli as client_cli

app = typer.Typer(pretty_exceptions_show_locals=True)
app.add_typer(client_cli.app, name="client-cli")
