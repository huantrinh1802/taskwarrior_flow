from tests import utils


def test_view_template(test_app):
    utils.pipe_input('\r')
    result = test_app["runner"].invoke(test_app["app"], ["utils", "view"])
    print(result.stdout)
    assert result.exit_code == 0
