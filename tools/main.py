import subprocess

import typer

from tools import group_mappings
from tools.utils import utils

app = typer.Typer()
app.add_typer(utils, name="utils", help="Sub-commands for taskwarrior utilities")


def task_wrapper(ctx: typer.Context):
    result = subprocess.run(
        f"{group_mappings[ctx.command.name]} task rc._forcecolor:on {' '.join(ctx.args)}",
        shell=True,
        capture_output=True,
        text=True,
    )
    print(result.stdout)


for group_name, _ in group_mappings.items():
    app.command(
        group_name, context_settings={"allow_extra_args": True}, help=f"Run taskwarrior with the {group_name} group"
    )(task_wrapper)


if __name__ == "__main__":
    app()
