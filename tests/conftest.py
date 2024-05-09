from pytest import fixture
from typer.testing import CliRunner

from tools.main import app
from tools.utils import get_preset_questions

runner = CliRunner()


@fixture(autouse=True, scope="session")
def setup_config():
    # TODO(BT): For some reason, tests require running get_preset_questions
    get_preset_questions('task', 'project')


@fixture
def test_app():
    return {"runner": runner, "app": app}
