from pytest import fixture
from typer.testing import CliRunner

runner = CliRunner()


@fixture(autouse=True, scope="session")
def setup_config():
    from tools.utils import get_preset_questions
    # TODO(BT): For some reason, tests require running get_preset_questions
    get_preset_questions("personal", "project")


@fixture
def test_app():
    from tools.main import app
    return {"runner": runner, "app": app}
