import json
import re
import subprocess
from typing import Annotated, Callable, TypedDict

import questionary
import typer
from prompt_toolkit.shortcuts import CompleteStyle
from rich import print as rprint

from tools import config_file, group_mappings, group_mappings_completion, tw_config

utils = typer.Typer()
question_style = questionary.Style(
    [
        ("qmark", "fg:#007777 bold"),  # token in front of the question
        ("question", "bold"),  # question text
        ("answer", "fg:white bg:#007777 "),  # submitted answer text behind the question
        ("pointer", "fg:#007777 bold"),  # pointer used in select and checkbox prompts
        ("highlighted", "fg:#007777 bold"),  # pointed-at choice in select and checkbox prompts
        ("selected", "fg:white"),  # style for a selected item of a checkbox
        ("separator", "fg:#008888"),  # separator in lists
        ("instruction", "fg:#858585"),  # user instructions for select, rawselect, checkbox
        ("text", ""),  # plain text
        ("disabled", "fg:#858585 italic"),  # disabled choices for select and checkbox prompts
    ]
)
projects = subprocess.run("task _projects", shell=True, capture_output=True).stdout.decode().split("\n")
tags = subprocess.run("task _tags", shell=True, capture_output=True).stdout.decode().split("\n")
preset_questions = {
    "project": questionary.autocomplete(
        "Enter project", choices=projects, style=question_style, complete_style=CompleteStyle.MULTI_COLUMN
    ),
    "tags": questionary.autocomplete(
        "Enter tags", choices=tags, style=question_style, complete_style=CompleteStyle.MULTI_COLUMN
    ),
}


class FunctionsGroup(TypedDict):
    func: Callable
    help: str


def safe_ask(question):
    try:
        response = question.unsafe_ask()
        return response
    except KeyboardInterrupt:
        print("Cancelled by user")
        return None


def create_query(*_):
    query_instruction = (
        "Use '|' for separate the filter and the report\ni.e. `project:TW | next`\n" if tw_config["use_mtwd"] else None
    )
    response = safe_ask(
        questionary.form(
            name=questionary.text("Enter name", style=question_style),
            query=questionary.text("Enter query", style=question_style, instruction=query_instruction),
        )
    )
    if response is None:
        return
    if response["name"] != "" and response["query"] != "":
        if tw_config["saved_queries"]["name_max_length"] < len(response["name"]):
            tw_config["saved_queries"]["name_max_length"] = len(response["name"])
        with open(config_file, "w") as f:
            tw_config["saved_queries"]["data"].append(response)
            f.write(json.dumps(tw_config))


def create_template(*_):
    response = safe_ask(
        questionary.form(
            name=questionary.text("Enter name", style=question_style),
            command=questionary.text("Enter command", style=question_style),
        )
    )
    if response is None:
        return
    template = {"name": response["name"], "command": response["command"], "fields": {}}
    print("<---------Fields--------->")
    field_name = "placeholder"
    while field_name != "":
        field_name = safe_ask(questionary.text("Enter field name", style=question_style))
        if field_name is None:
            return
        if field_name != "":
            field_template = safe_ask(questionary.text("Enter field template", style=question_style))
            if field_template is None:
                return
            template["fields"][field_name] = field_template
            print("To end enter nothing")
    with open(config_file, "w") as f:
        tw_config["add_templates"]["data"].append(template)
        f.write(json.dumps(tw_config))


def create_task(group):
    templates = [
        questionary.Choice(title=template["name"], value=index, shortcut_key=str(index + 1))
        for index, template in enumerate(tw_config["add_templates"]["data"])
    ]
    chosen_template = safe_ask(
        questionary.rawselect("Select template", choices=templates, use_jk_keys=True, style=question_style)
    )
    if chosen_template is None:
        return
    questions = {}
    for name, field in tw_config["add_templates"]["data"][chosen_template]["fields"].items():
        if name in preset_questions:
            questions[name] = preset_questions[name]
        else:
            questions[name] = questionary.text(f"Enter {name}", instruction="Use ';' for list\n", style=question_style)
    answers = safe_ask(questionary.form(**questions))
    if answers is None:
        return
    parts = ""
    annotations: None | list[str] = None
    for name, field in tw_config["add_templates"]["data"][chosen_template]["fields"].items():
        value = answers.get(name, "")
        if len(value) != 0 or answers[name] != " ":
            if name in "annotations":
                annotations = [annotation for annotation in answers[name].split(";")]
            else:
                parts += " " + " ".join(
                    field.replace("%s", item) if item != "" else "" for item in answers[name].split(";")
                )
    command = tw_config["add_templates"]["data"][chosen_template]["command"].replace("%s", parts)
    confirm = safe_ask(questionary.confirm("Add task?", instruction=f"\n{command}\n", style=question_style))
    if confirm:
        uuid_compiled = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
        result = subprocess.run(
            f"{group_mappings[group]} task rc.verbose=new-uuid {command}",
            capture_output=True,
            text=True,
            shell=True,
        )
        print(result.stdout)
        uuid_match = uuid_compiled.search(result.stdout)
        if uuid_match:
            uuid = uuid_match.group()
            if annotations:
                for annotate in annotations:
                    result = subprocess.run(
                        f"{group_mappings[group]} task {uuid} annotate {annotate}",
                        capture_output=True,
                        text=True,
                        shell=True,
                    )


def create_group():
    result = safe_ask(
        questionary.form(
            name=questionary.text("Enter name", style=question_style),
            data_location=questionary.text("Enter data location", style=question_style),
        )
    )
    if result is None:
        return
    if result["name"] != "" and result["data_location"] != "":
        tw_config["flow_config"].update({result["name"]: result["data_location"]})
    with open(config_file, "w") as f:
        f.write(json.dumps(tw_config))


create_groups: dict[str, FunctionsGroup] = {
    "task": {"help": "Add a new task based on template", "func": create_task},
    "template": {"help": "Add a new task template", "func": create_template},
    "query": {"help": "Add a new query for viewing tasks", "func": create_query},
    "group": {"help": "Add a new group of tasks", "func": create_group},
}


def create_group_completion():
    auto_completions = []
    for key, value in create_groups.items():
        auto_completions.append((key, value["help"]))
    return auto_completions


@utils.command("add", help="Add task, query, and template")
def task_create(
    name: Annotated[str, typer.Argument(autocompletion=create_group_completion)] = "task",
    group: Annotated[str, typer.Option("--group", "-g", autocompletion=group_mappings_completion)] = "task",
):
    create_groups[name]["func"](group)


def edit_template():
    templates = [
        questionary.Choice(title=template["name"], value=index, shortcut_key=str(index + 1))
        for index, template in enumerate(tw_config["add_templates"]["data"])
    ]
    chosen_template = safe_ask(
        questionary.rawselect("Select template", choices=templates, use_jk_keys=True, style=question_style)
    )
    if chosen_template is None:
        return
    response = safe_ask(
        questionary.form(
            name=questionary.text(
                "Enter name", style=question_style, default=tw_config["add_templates"]["data"][chosen_template]["name"]
            ),
            command=questionary.text(
                "Enter command",
                style=question_style,
                default=tw_config["add_templates"]["data"][chosen_template]["command"],
            ),
        )
    )
    if response is None:
        return
    template = {"name": response["name"], "command": response["command"], "fields": {}}
    for name, field_template in tw_config["add_templates"]["data"][chosen_template]["fields"].items():
        response = safe_ask(
            questionary.form(
                name=questionary.text("Enter field name", style=question_style, default=name),
                template=questionary.text("Enter field template", style=question_style, default=field_template),
            )
        )
        if response is None:
            return
        template["fields"][response["name"]] = response["template"]
    field_name = "placeholder"
    while field_name != "":
        field_name = safe_ask(questionary.text("Enter field name", style=question_style))
        if field_name is None:
            return
        if field_name != "":
            field_template = safe_ask(questionary.text("Enter field template", style=question_style))
            if field_template is None:
                return
            template["fields"][field_name] = field_template
            print("To end enter nothing")
    tw_config["add_templates"]["data"][chosen_template] = template
    with open(config_file, "w") as f:
        f.write(json.dumps(tw_config))


def edit_query():
    max_length = tw_config["saved_queries"]["name_max_length"]
    queries = [
        questionary.Choice(
            title=f"{query['name'].ljust(max_length)} | {query['query']}", value=index, shortcut_key=str(index + 1)
        )
        for index, query in enumerate(tw_config["saved_queries"]["data"])
    ]
    chosen_query = safe_ask(
        questionary.rawselect("Select query", choices=queries, use_jk_keys=True, style=question_style)
    )
    if chosen_query is None:
        return
    response = safe_ask(
        questionary.form(
            name=questionary.text(
                "Enter name", style=question_style, default=tw_config["saved_queries"]["data"][chosen_query]["name"]
            ),
            query=questionary.text(
                "Enter query", style=question_style, default=tw_config["saved_queries"]["data"][chosen_query]["query"]
            ),
        )
    )
    if response is None:
        return
    if response["name"] != "" and response["query"] != "":
        if tw_config["saved_queries"]["name_max_length"] < len(response["name"]):
            tw_config["saved_queries"]["name_max_length"] = len(response["name"])
        with open(config_file, "w") as f:
            tw_config["saved_queries"]["data"][chosen_query] = response
            f.write(json.dumps(tw_config))


def edit_group():
    groups = [
        questionary.Choice(
            title=f"{group_name}\nData: {group_config['data']}\nConfig: {group_config['config']}",
            value=group_name,
            shortcut_key=str(index + 1),
        )
        for index, (group_name, group_config) in enumerate(tw_config["flow_config"].items())
    ]

    chosen_group = safe_ask(
        questionary.rawselect("Select group", choices=groups, use_jk_keys=True, style=question_style)
    )

    if chosen_group is None:
        return

    response = safe_ask(
        questionary.form(
            name=questionary.text("Enter name", style=question_style, default=chosen_group),
            data=questionary.text(
                "Enter data location",
                style=question_style,
                default=tw_config["flow_config"][chosen_group]["data"],
            ),
            config=questionary.text(
                "Enter config location",
                style=question_style,
                default=tw_config["flow_config"][chosen_group]["config"],
            ),
        )
    )
    if response is None:
        return
    if response["name"] != "" and response["data"] != "" and response["config"] != "":
        tw_config["flow_config"][response["name"]] = {"data": response["data"], "config": response["config"]}
        with open(config_file, "w") as f:
            f.write(json.dumps(tw_config))


edit_groups: dict[str, FunctionsGroup] = {
    "template": {"help": "Edit task template", "func": edit_template},
    "query": {"help": "Edit view query", "func": edit_query},
    "group": {"help": "Edit group of tasks", "func": edit_group},
}


def edit_group_completion():
    auto_completions = []
    for group, group_info in edit_groups.items():
        auto_completions.append((group, group_info["help"]))
    return auto_completions


@utils.command("edit", help="Edit query, and template")
def task_edit(
    name: Annotated[str, typer.Argument(autocompletion=edit_group_completion)] = "template",
):
    edit_groups[name]["func"]()


def view_task():
    max_length = tw_config["saved_queries"]["name_max_length"]
    queries = [
        questionary.Choice(
            title=f"{query['name'].ljust(max_length)} | {query['query']}", value=index, shortcut_key=str(index + 1)
        )
        for index, query in enumerate(tw_config["saved_queries"]["data"])
    ]
    chosen_query = safe_ask(
        questionary.rawselect("Select query", choices=queries, use_jk_keys=True, style=question_style)
    )
    if chosen_query is None:
        return
    command = tw_config["saved_queries"]["data"][chosen_query]["query"].replace("|", " ")
    output = subprocess.run(f"task rc._forcecolor:on {command}", shell=True, capture_output=True, text=True)
    print(output.stdout)


def view_template():
    templates = [
        questionary.Choice(title=template["name"], value=index, shortcut_key=str(index + 1))
        for index, template in enumerate(tw_config["add_templates"]["data"])
    ]
    chosen_template = safe_ask(
        questionary.rawselect("Select template", choices=templates, use_jk_keys=True, style=question_style)
    )
    if chosen_template is None:
        return
    header = f'[bold]Template:[/bold] {tw_config["add_templates"]["data"][chosen_template]["name"]}'
    field_header = f'{"-"*10}Fields{"-"*10}'
    rprint(
        f"""{header}
[bold]Command:[/bold] {tw_config["add_templates"]["data"][chosen_template]["command"]}
[bold]{field_header}[/bold]"""
    )
    for name, field_template in tw_config["add_templates"]["data"][chosen_template]["fields"].items():
        rprint(f"{name.ljust(16)} | {field_template}")


view_groups: dict[str, FunctionsGroup] = {
    "task": {"help": "View tasks based on saved queries", "func": view_task},
    "template": {"help": "View the details of the template", "func": view_template},
}


def view_group_completion():
    auto_completions = []
    for key, value in view_groups.items():
        auto_completions.append((key, value["help"]))
    return auto_completions


@utils.command("view", help="View task and template")
def task_view(
    name: Annotated[str, typer.Argument(autocompletion=view_group_completion)] = "task",
):
    view_groups[name]["func"]()
