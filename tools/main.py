import re
import subprocess

import dateparser
import questionary
import typer

from tools import group_mappings
from tools.utils import question_style, safe_ask, utils

app = typer.Typer()
app.add_typer(utils, name="utils", help="Sub-commands for taskwarrior utilities")
date_function_compiled = re.compile(r"@(?P<date>.*)@")


def task_wrapper(ctx: typer.Context):
    command = ""
    func_start = False
    func = ""
    for arg in ctx.args:
        if ":@" in arg and not arg.endswith("@"):
            func_start = True
            func += arg
            continue
        if ":@" in arg and arg.endswith("@"):
            func = arg
        if func_start:
            func += " " + arg
            if not arg.endswith("@"):
                continue
        if func != "" and func.endswith("@"):
            func_start = False
            date_match = date_function_compiled.search(func)
            if date_match:
                parsed = dateparser.parse(date_match.groupdict("date")["date"])
                if parsed:
                    parsed = parsed.strftime("%Y-%m-%dT%H:%M:%S")
                    arg = date_function_compiled.sub(parsed, func)
            func = ""
        command += " " + arg
    confirm = safe_ask(questionary.confirm("Add task?", instruction=f"\n{command}\n", style=question_style))
    if confirm:
        result = subprocess.run(
            f"{group_mappings[ctx.command.name]} task rc._forcecolor:on {command}",
            shell=True,
            capture_output=True,
            text=True,
        )
        print(result.stderr)
        print(result.stdout)


for group_name, _ in group_mappings.items():
    app.command(
        group_name, context_settings={"allow_extra_args": True}, help=f"Run taskwarrior with the {group_name} group"
    )(task_wrapper)


if __name__ == "__main__":
    app()
