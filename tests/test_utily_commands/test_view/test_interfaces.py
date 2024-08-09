from unittest.mock import patch


@patch("questionary.rawselect")
def test_view_template(mock_rawselect, test_app):
    mock_rawselect.return_value.unsafe_ask.return_value = 0
    result = test_app["runner"].invoke(test_app["app"], ["utils", "view", "template"])
    assert result.exit_code == 0


@patch("questionary.rawselect")
def test_view_task(mock_rawselect, test_app):
    mock_rawselect.return_value.unsafe_ask.return_value = 0
    result = test_app["runner"].invoke(test_app["app"], ["utils", "view", "task"])
    assert result.exit_code == 0
