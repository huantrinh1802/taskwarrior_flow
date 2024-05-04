from typer.testing import CliRunner

from tools.main import app

runner = CliRunner()


def test_app():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "task" in result.stdout
    assert "utils" in result.stdout
