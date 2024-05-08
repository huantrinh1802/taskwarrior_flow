from pytest import fixture
from typer.testing import CliRunner

from tools.main import app
from tools.utils import get_preset_questions

runner = CliRunner()


@fixture
def test_app():
    # TODO(BT): For some reason, this test require running get_preset_questions
    get_preset_questions(None)
    return {"runner": runner, "app": app}
