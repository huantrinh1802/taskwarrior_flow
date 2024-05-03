import subprocess
from typing import Annotated

import typer

from tools import group_mappings, group_mappings_completion
from tools.utils import utils

app = typer.Typer()
app.add_typer(utils, name="utils", help="Sub-commands for taskwarrior utilities")


@app.command(context_settings={"allow_extra_args": True}, help="Run taskwarrior with the given data group")
def task(
    ctx: typer.Context,
    group: Annotated[str, typer.Option("--group", "-g", autocompletion=group_mappings_completion)] = "default",
):
    result = subprocess.run(
        f"{group_mappings[group]} task rc._forcecolor:on {' '.join(ctx.args)}",
        shell=True,
        capture_output=True,
        text=True,
    )
    print(result.stdout)


if __name__ == "__main__":
    app()
