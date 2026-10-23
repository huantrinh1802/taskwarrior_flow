import json
import os
import subprocess
import sys


def test_first_run_creates_missing_config_dir(tmp_path):
    config_file = tmp_path / "missing" / "tw_flow" / "config.json"
    env = {**os.environ, "TW_CONFIG": str(config_file)}
    result = subprocess.run(
        [sys.executable, "-c", "import tools"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert config_file.is_file()
    assert "flow_config" in json.loads(config_file.read_text())
