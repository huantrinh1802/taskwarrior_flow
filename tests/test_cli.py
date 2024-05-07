def test_app(test_app):
    result = test_app["runner"].invoke(test_app["app"], ["--help"])
    assert result.exit_code == 0
    assert "task" in result.stdout
    assert "utils" in result.stdout
