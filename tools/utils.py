import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from typing import Annotated, Callable, TypedDict

import dateparser
import questionary
import typer
from prompt_toolkit.shortcuts import CompleteStyle
from rich import print as rprint

from tools import config_file, group_mappings, group_mappings_completion, tw_config

utils_commands = typer.Typer()
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
preset_questions = ["project", "tags"]


def date_parser(date_str):
    result = subprocess.run(f"task calc {date_str}", capture_output=True, text=True, shell=True)
    if (
        result.stderr
        or result.stdout.replace("\n", "") == ""
        or result.stdout.replace("\n", "") == date_str
        or "P" in result.stdout
    ):
        parsed = dateparser.parse(date_str)
        if parsed:
            return parsed
        else:
            return None
    else:
        return datetime.fromisoformat(result.stdout.strip("\n"))


def get_preset_questions(group, field):
    projects = (
        subprocess.run(f"{group_mappings[group]} task _projects", shell=True, capture_output=True)
        .stdout.decode()
        .split("\n")
    )
    tags = (
        subprocess.run(f"{group_mappings[group]} task _tags", shell=True, capture_output=True)
        .stdout.decode()
        .split("\n")
    )
    match field:
        case "project":
            return questionary.autocomplete(
                "Enter project",
                choices=projects,
                style=question_style,
                complete_style=CompleteStyle.MULTI_COLUMN,
            )
        case "tags":
            return questionary.autocomplete(
                "Enter tags",
                choices=tags,
                style=question_style,
                complete_style=CompleteStyle.MULTI_COLUMN,
            )
    return None


class FunctionsGroup(TypedDict):
    func: Callable
    help: str


class DateValidator(questionary.Validator):
    def validate(self, document):  # type: ignore
        result = subprocess.run(f"task calc {document.text}", capture_output=True, text=True, shell=True)
        if (
            result.stderr
            or result.stdout == ""
            or result.stdout.replace("\n", "") == document.text
            or "P" in result.stdout
        ):
            if dateparser.parse(document.text) or len(document.text) == 0:
                return True
            else:
                raise questionary.ValidationError(
                    message="Invalid date",
                    cursor_position=len(document.text),
                )
        else:
            return True


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
            field_form = safe_ask(
                questionary.form(
                    template=questionary.text("Enter field template", style=question_style),
                    type=questionary.rawselect(
                        "Select type of the field",
                        choices=["text", "list", "date", "annotation"],
                        default="text",
                        use_jk_keys=True,
                        style=question_style,
                    ),
                    repeat=questionary.confirm(
                        "Repeat field?", style=question_style, default=True, instruction="Leave blank to end"
                    ),
                )
            )
            if field_form is None:
                return
            template["fields"][field_name] = field_form
            print("To end enter nothing")
    with open(config_file, "w") as f:
        tw_config["add_templates"]["data"].append(template)
        f.write(json.dumps(tw_config))


def create_task(group, chosen_template = None, answers = {}) -> None | dict:
    if chosen_template is None:
        return
    for name, field in tw_config["add_templates"]["data"][chosen_template]["fields"].items():
        if name in answers and field.get('repeat', False):
            continue
        if field["type"] == ["list", "annotation"]:
            answer = "placeholder"
            answers[name] = []
            while answer != "" and answer is not None:
                if name in preset_questions:
                    answer = safe_ask(get_preset_questions(group, name))
                else:
                    answer = safe_ask(
                        questionary.text(f"Enter {name}", style=question_style, instruction="Leave blank to stop\n")
                    )
                if answer is not None:
                    if answer != "":
                        answers[name].append(answer)
                        questionary.print("Leave blank to stop", style="fg:#858585")
                else:
                    return
        elif field["type"] == "date":
            answer = safe_ask(questionary.text(f"Enter {name}", style=question_style, validate=DateValidator))
            if answer is None:
                return
            answers[name] = answer
        else:
            if name in preset_questions:
                answer = safe_ask(get_preset_questions(group, name))
                if answer is None:
                    return
                answers[name] = answer
            else:
                answer = safe_ask(
                    questionary.text(f"Enter {name}", style=question_style, instruction="Leave blank to stop\n")
                )
                if answer is None:
                    return
                answers[name] = answer
    if len(answers) == 0:
        return
    parts = ""
    annotations: None | list[str] = None
    for name, field in tw_config["add_templates"]["data"][chosen_template]["fields"].items():
        value = answers.get(name, "")
        if len(value) != 0 or value != " ":
            if field["type"] == "annotation":
                annotations = [annotation for annotation in answers[name]]
            elif field["type"] == "date":
                date_value = date_parser(answers[name])
                if date_value is not None:
                    date_str = date_value.strftime("%Y-%m-%dT%H:%M:%S")
                    parts += " " + field["template"].replace("%s", date_str)
                else:
                    print('Cannot parse date "%s"' % answers[name])
                    return
            elif field["type"] == "list":
                parts += " " + " ".join(
                    field["template"].replace("%s", item) if item != "" else "" for item in answers[name]
                )
            else:
                parts += " " + field["template"].replace("%s", value)
    command = tw_config["add_templates"]["data"][chosen_template]["command"].replace("%s", parts)
    confirm = "edit"
    while confirm == "edit":
        confirm = safe_ask(
            questionary.rawselect(
                "Add task?",
                choices=["yes", "edit", "no"],
                default="yes",
                instruction=f"\n{command}\n",
                style=question_style,
            )
        )
        match confirm:
            case "yes":
                uuid_compiled = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
                result = subprocess.run(
                    f"{group_mappings[group]} task rc.verbose=new-uuid add {command}",
                    capture_output=True,
                    text=True,
                    shell=True,
                )
                if result.stderr:
                    print(result.stderr)
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
                return answers
            case "edit":
                if isinstance(command, str):
                    command = safe_ask(questionary.text("Edit command", style=question_style, default=command))
                else:
                    print("Cannot edit command")
            case "no":
                print("Cancelled by user")
                return


def create_group(*_):
    result = safe_ask(
        questionary.form(
            name=questionary.text("Enter name", style=question_style),
            data=questionary.text("Enter data location", style=question_style),
            config=questionary.text("Enter config location", style=question_style),
        )
    )
    if result is None:
        return
    if result["name"] != "" and result["data"] != "" and result["config"] != "":
        tw_config["flow_config"].update({result["name"]: {"data": result["data"], "config": result["config"]}})
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


@utils_commands.command("add", help="Add task, query, and template")
def task_create(
    name: Annotated[str, typer.Argument(autocompletion=create_group_completion)] = "task",
    group: Annotated[str, typer.Option("--group", "-g", autocompletion=group_mappings_completion)] = "task",
    repeat: Annotated[bool, typer.Option("--repeat", "-r")] = False,
):
    repeating = True
    if name == 'task':
        templates = [
            questionary.Choice(title=template["name"], value=index, shortcut_key=str(index + 1))
            for index, template in enumerate(tw_config["add_templates"]["data"])
        ]
        chosen_template = safe_ask(
            questionary.rawselect("Select template", choices=templates, use_jk_keys=True, style=question_style)
        )
        answers = {}
        while repeating:
            answers = create_task(group, chosen_template, answers)
            if answers is None:
                repeating = False
            elif repeat:
                confirm = safe_ask(questionary.confirm("Add more task?", style=question_style))
                if confirm:
                    repeating = True
                else:
                    repeating = False
            else:
                repeating = False
    else:
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
    for name, field in tw_config["add_templates"]["data"][chosen_template]["fields"].items():
        response = safe_ask(
            questionary.form(
                name=questionary.text("Enter field name", style=question_style, default=name),
                template=questionary.text("Enter field template", style=question_style, default=field.get("template","") or ""),
                type=questionary.rawselect(
                    "Select type",
                    choices=["text", "list", "date", "annotation"],
                    use_jk_keys=True,
                    style=question_style,
                    default=field["type"],
                ),
                repeat=questionary.confirm("Repeat field?", style=question_style, default=True),
            )
        )
        if response is None:
            return
        template["fields"][response["name"]] = response
    field_name = "placeholder"
    while field_name != "":
        field_name = safe_ask(questionary.text("Enter field name", style=question_style))
        if field_name is None:
            return
        if field_name != "":
            field_form = safe_ask(
                questionary.form(
                    template=questionary.text("Enter field template", style=question_style),
                    type=questionary.rawselect(
                        "Select type of the field",
                        choices=["text", "list", "date", "annotation"],
                        default="text",
                        use_jk_keys=True,
                        style=question_style,
                    ),
                    repeat=questionary.confirm("Repeat field?", style=question_style, default=True),

                )
            )
            if field_form is None:
                return
            template["fields"][field_name] = field_form
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


@utils_commands.command("edit", help="Edit query, and template")
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
    field_header = f'{"-"*33} Fields {"-"*32}'
    rprint(
        f"""{header}
[bold]Command:[/bold] {tw_config["add_templates"]["data"][chosen_template]["command"]}
[bold]{field_header}[/bold]"""
    )
    rprint(f"{'name'.ljust(16)} | {'template'.ljust(16)} | {'type'.ljust(16)} | repeat")
    rprint(f"{'-'*16} | {'-'*16} | {'-'*16} | {'-'*16}")
    for name, field in tw_config["add_templates"]["data"][chosen_template]["fields"].items():
        rprint(f"{name.ljust(16)} | {(field.get('template') or '').ljust(16)} | {field['type'].ljust(16)} | {field.get('repeat', False)}")


view_groups: dict[str, FunctionsGroup] = {
    "task": {"help": "View tasks based on saved queries", "func": view_task},
    "template": {"help": "View the details of the template", "func": view_template},
}


def view_group_completion():
    auto_completions = []
    for key, value in view_groups.items():
        auto_completions.append((key, value["help"]))
    return auto_completions


@utils_commands.command("view", help="View task and template")
def task_view(
    name: Annotated[str, typer.Argument(autocompletion=view_group_completion)] = "task",
):
    view_groups[name]["func"]()


def delete_template():
    templates = [
        questionary.Choice(title=template["name"], value=index, shortcut_key=str(index + 1))
        for index, template in enumerate(tw_config["add_templates"]["data"])
    ]
    chosen_template = safe_ask(
        questionary.rawselect("Select template", choices=templates, use_jk_keys=True, style=question_style)
    )
    if chosen_template is None:
        return
    confirm = safe_ask(
        questionary.confirm(
            f"Delete template {tw_config['add_templates']['data'][chosen_template]['name']}", style=question_style
        )
    )
    if confirm:
        tw_config["add_templates"]["data"].pop(chosen_template)
        with open(config_file, "w") as f:
            f.write(json.dumps(tw_config))


def delete_query():
    pass
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
    confirm = safe_ask(
        questionary.confirm(
            f"Delete query {tw_config['saved_queries']['data'][chosen_query]['name']}", style=question_style
        )
    )
    if confirm:
        tw_config["saved_queries"]["data"].pop(chosen_query)
        for query in tw_config["saved_queries"]["data"]:
            if max_length < len(query["name"]):
                max_length = len(query["name"])
        tw_config["saved_queries"]["name_max_length"] = max_length

        with open(config_file, "w") as f:
            f.write(json.dumps(tw_config))


def delete_group():
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
    confirm = safe_ask(questionary.confirm(f"Delete group {chosen_group}?", style=question_style))
    if confirm:
        deleted_group = tw_config["flow_config"].pop(chosen_group)
        with open(config_file, "w") as f:
            f.write(json.dumps(tw_config))
        data_confirm = safe_ask(
            questionary.confirm(f"Delete data location {deleted_group['data']}", style=question_style)
        )
        if data_confirm:
            data_path = deleted_group["data"].replace("~", os.path.expanduser("~"))
            if os.path.isdir(data_path):
                shutil.rmtree(data_path)
        config_confirm = safe_ask(
            questionary.confirm(f"Delete config location {deleted_group['config']}", style=question_style)
        )
        if config_confirm:
            config_path = deleted_group["config"].replace("~", os.path.expanduser("~"))
            if os.path.isfile(config_path):
                shutil.rmtree(config_path)


delete_groups: dict[str, FunctionsGroup] = {
    "template": {"help": "Delete template", "func": delete_template},
    "query": {"help": "Delete query", "func": delete_query},
    "group": {"help": "Delete group", "func": delete_group},
}


def delete_group_completion():
    auto_completions = []
    for key, value in delete_groups.items():
        auto_completions.append((key, value["help"]))
    return auto_completions


@utils_commands.command("delete", help="Delete task, query, template, and group")
def task_delete(name: Annotated[str, typer.Argument(autocompletion=edit_group_completion)] = "template"):
    delete_groups[name]["func"]()
