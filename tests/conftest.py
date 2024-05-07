from pytest import fixture
from typer.testing import CliRunner

from tools.main import app

runner = CliRunner()


@fixture
def test_app():
    return {"runner": runner, "app": app}
