import json
import os

TEST_CONFIG = {
    "use_mtwd": False,
    "flow_config": {
        "personal": {"data": "~/.task", "config": "~/.taskrc"},
        "test": {"data": "~/.task_test", "config": "~/.taskrc"},
    },
    "add_templates": {
        "date_fields": ["due", "scheduled"],
        "data": [
            {
                "name": "Bills",
                "command": "%s +TDBillsS +bill +home +todoist +utility wait:due-1day",
                "fields": {
                    "description": {"template": "'%s'", "type": "text"},
                },
            },
        ],
    },
    "saved_queries": {
        "name_max_length": 14,
        "data": [{"query": "project:Test", "name": "Test project"}],
    },
    "ai": {
        "provider": "anthropic",
        "anthropic_api_key": "",
        "openai_api_key": "",
    },
}


def pytest_configure(config):
    """Write the test config before any tools module is imported."""
    config_path = os.environ.get("TW_CONFIG")
    if config_path:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w") as f:
            f.write(json.dumps(TEST_CONFIG))
