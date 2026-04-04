"""Stack Bench CLI -- backend organism.

Usage: python -m organisms.cli.main [COMMAND]
"""

from __future__ import annotations

import typer

from organisms.cli.stack_commands import app as stack_app

app = typer.Typer(name="sb", help="Stack Bench CLI")
app.add_typer(stack_app, name="stack")

if __name__ == "__main__":
    app()
