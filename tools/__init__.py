import json
import os

config_file = os.environ.get("TW_CONFIG", f'{os.path.expanduser("~")}/.local/share/tw_flow/config.json')
if os.path.isfile(config_file):
    with open(config_file, "r") as f:
        tw_config = json.load(f)
else:
    with open(config_file, "w") as f:
        tw_config = {
            "use_mtwd": False,
            "flow_config": {
                "personal": {"data": "~/.task", "config": "~/.taskrc"},
            },
            "add_templates": {
                "date_fields": ["due", "scheduled"],
                "data": [
                ],
            },
            "saved_queries": {
                "name_max_length": 14,
                "data": [],
            },
            "ai": {
                "provider": "anthropic",
                "anthropic_api_key": "",
                "openai_api_key": "",
                "anthropic_model": "",
                "openai_model": "",
            },
        }
        f.write(json.dumps(tw_config))
group_mappings = {key: f'TASKDATA={value["data"]}' for key, value in tw_config["flow_config"].items()}


def group_mappings_completion():
    autocompletions = []
    for key in group_mappings:
        autocompletions.append((key, f"Taskwarrior data group: {key}"))
    return autocompletions
