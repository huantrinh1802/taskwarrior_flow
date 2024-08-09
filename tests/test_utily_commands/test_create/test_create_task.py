from unittest.mock import patch


@patch('questionary.rawselect')
def test_create_task_0(mock_rawselect, test_app):
    mock_rawselect.return_value.unsafe_ask.return_value = 0
    result = test_app["runner"].invoke(test_app["app"], ["utils", "view", "template"])
    assert """Template: Bills
Command: %s +TDBillsS +bill +home +todoist +utility wait:due-1day
--------------------------------- Fields --------------------------------
name             | template         | type             | repeat
---------------- | ---------------- | ---------------- | ----------------
description      | '%s'             | text             | False
""" in result.stdout

def test_create_task_1(test_app):
    with patch('questionary.text') as mock_text, patch('questionary.rawselect') as mock_rawselect:
        mock_rawselect.return_value.unsafe_ask.side_effect = [0, 'yes']
        mock_text.return_value.unsafe_ask.return_value = "Test"
        result = test_app["runner"].invoke(test_app["app"], ["utils", "add", "task", "-g", "test"])
        assert result.exit_code == 0
