import json
import os

config_file = os.environ.get("TW_CONFIG", f'{os.path.expanduser("~")}/.local/share/nvim/m_taskwarrior_d.json')
if os.path.isfile(config_file):
    with open(config_file) as f:
        tw_config = json.load(f)
else:
    with open(config_file) as f:
        tw_config = {
            "use_mtwd": False,
            "flow_config": {"default": {"data": "~/.task", "config": "~/.taskrc"}},
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
