import os
import re
import subprocess
from datetime import datetime
from typing import Annotated, Optional

import dateparser
import questionary
import typer

from tools import group_mappings, group_mappings_completion, tw_config
from tools.utils import question_style, safe_ask, utils_commands

app = typer.Typer()
app.add_typer(utils_commands, name="utils", help="Sub-commands for taskwarrior utilities")
date_function_compiled = re.compile(r"@(?P<date>.*)@")


def task_wrapper(ctx: typer.Context):
    # TODO(BT - 2024-01-01): #HUM-323 asdfsfs 
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


@app.command()
def ai(
    prompt: Annotated[list[str], typer.Argument(help="Natural language task description")],
    group: Annotated[Optional[str], typer.Option("--group", "-g", help="Task group to use", autocompletion=group_mappings_completion)] = None,
    provider: Annotated[Optional[str], typer.Option("--provider", "-p", help="AI provider: anthropic or openai")] = None,
):
    """Parse a natural language prompt into a Taskwarrior command using AI."""
    from tools.ai import parse_nl_to_command

    resolved_group = group or next(iter(group_mappings))

    if resolved_group not in group_mappings:
        typer.echo(f"Unknown group '{resolved_group}'. Available: {', '.join(group_mappings.keys())}", err=True)
        raise typer.Exit(1)

    ai_config = tw_config.get("ai", {})
    # Resolution order: CLI flag > env var > TW_CONFIG > default
    resolved_provider = provider or os.environ.get("TW_AI_PROVIDER") or ai_config.get("provider", "anthropic")
    # Env var takes precedence over config file for keys
    config_api_key = ai_config.get(f"{resolved_provider}_api_key") or None

    nl_prompt = " ".join(prompt)
    try:
        command = parse_nl_to_command(nl_prompt, resolved_provider, config_api_key)  # type: ignore[arg-type]
    except (ImportError, ValueError) as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    confirm = safe_ask(questionary.confirm("Confirm?", instruction=f"\n{command}\n", style=question_style))
    if confirm:
        result = subprocess.run(
            f"{group_mappings[resolved_group]} task rc._forcecolor:on {command}",
            shell=True,
            capture_output=True,
            text=True,
        )
        print(result.stderr)
        print(result.stdout)


if __name__ == "__main__":
    app()
