"""Typer command-line front-end for the ProtoDUNE conditions client.

Installs the ``pd-cds`` console script. Global connection options
(server, proxy, cache TTL, verbosity) are defined on the app callback in
:func:`pd_cds_cli.main.main`; queries run through the
:class:`pd_cds_api.ApiClientWrapper` API. See client/pd-cds-cli/README.md
for user documentation.
"""
