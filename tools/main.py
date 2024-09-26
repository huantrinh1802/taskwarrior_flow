import re
import subprocess
from datetime import datetime

import dateparser
import questionary
import typer

from tools import group_mappings
from tools.utils import question_style, safe_ask, utils_commands

app = typer.Typer()
app.add_typer(utils_commands, name="utils", help="Sub-commands for taskwarrior utilities")
date_function_compiled = re.compile(r"@(?P<date>.*)@")


def task_wrapper(ctx: typer.Context):
    command = ""
    func_start = False
    func = ""
    description_start = False
    description = ""
    keywords = ["add", "mod", "delete"]
    keywords_seen = False
    for index, arg in enumerate(ctx.args):
        if arg in keywords and not keywords_seen:
            keywords_seen = True
        elif (
            index != len(ctx.args) - 1
            and keywords_seen
            and not func_start
            and not arg.startswith(("+", "due:", "scheduled:", "wait:", "until:", "priority:", "recur:", "project:"))
        ):
            description_start = True
            description += " " + arg
            continue
        elif keywords_seen and not func_start and description_start:
            if index == len(ctx.args) - 1 and not arg.startswith(
                ("+", "due:", "scheduled:", "wait:", "until:", "priority:", "recur:", "project:")
            ):
                description_start = False
                description += " " + arg
                description = description.lstrip(" ").rstrip(" ").replace("'", "").replace('"', "")
                arg = f'"{description}"'
            else:
                description_start = False
                description = description.lstrip(" ").rstrip(" ").replace("'", "").replace('"', "")
                arg = f'"{description}" {arg}'
        # Note(BT): extract @date@
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
                if parsed and isinstance(parsed, datetime):
                    parsed_str = parsed.strftime("%Y-%m-%dT%H:%M:%S")
                    if parsed_str:
                        print(f"Invalid date format: {date_match.groupdict('date')['date']}")
                        return
                    arg = date_function_compiled.sub(parsed_str, func)
                else:
                    print(f"Invalid date format: {date_match.groupdict('date')['date']}")
                    return
            func = ""
        # end of extract @date@
        command += " " + arg
    if any(keyword in command for keyword in ["add", "mod"]):
        confirm = safe_ask(questionary.confirm("Confirm?", instruction=f"\n{command}\n", style=question_style))
    else:
        confirm = True
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
        group_name, context_settings={"allow_extra_args": True}, help=f"Run Taskwarrior with the {group_name} group"
    )(task_wrapper)


if __name__ == "__main__":
    app()
