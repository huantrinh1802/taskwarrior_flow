import json
import os

config_file = os.environ.get("TW_CONFIG", f'{os.path.expanduser("~")}/.local/share/nvim/m_taskwarrior_d.json')
if os.path.isfile(config_file):
    with open(config_file, "r") as f:
        tw_config = json.load(f)
else:
    if config_file == "/tmp/m_taskwarrior_d.json":
        with open(config_file, "w") as f:
            tw_config = {
                "use_mtwd": False,
                "flow_config": {
                    "task": {"data": "~/.task", "config": "~/.taskrc"},
                    "work": {"data": "~/.task_work", "config": "~/.taskrc"},
                    "test": {"data": "~/.task_test", "config": "~/.taskrc"},
                },
                "add_templates": {
                    "date_fields": ["due", "scheduled"],
                    "data": [
                        {
                            "name": "Bills",
                            "command": "add %s +TDBillsS +bill +home +todoist +utility wait:due-1day",
                            "fields": {
                                "description": {"template": "'%s'", "type": "text"},
                                "project": {"template": "project:%s", "type": "text"},
                                "due": {"template": "due:%s", "type": "date"},
                            },
                        },
                    ],
                },
                "saved_queries": {
                    "name_max_length": 14,
                    "data": [{"query": "project:Test", "name": "Test project"}],
                },
            }
            f.write(json.dumps(tw_config))
    else:
        with open(config_file, "w") as f:
            tw_config = {
                "use_mtwd": False,
                "flow_config": {"task": {"data": "~/.task", "config": "~/.taskrc"}},
                "add_templates": {"data": []},
                "saved_queries": {"name_max_length": 0, "data": []},
            }
            f.write(json.dumps(tw_config))
group_mappings = {key: f'TASKDATA={value["data"]}' for key, value in tw_config["flow_config"].items()}


def group_mappings_completion():
    autocompletions = []
    for key in group_mappings:
        autocompletions.append((key, f"Taskwarrior data group: {key}"))
    return autocompletions
