import pytest
from typer.testing import CliRunner

from drudgeyer import app

runner = CliRunner()


@pytest.mark.cli
def test_app():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0, result.stdout

    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0, result.stdout

    result = runner.invoke(app, ["add", "--help"])
    assert result.exit_code == 0, result.stdout

    result = runner.invoke(app, ["list", "--help"])
    assert result.exit_code == 0, result.stdout

    result = runner.invoke(app, ["delete", "--help"])
    assert result.exit_code == 0, result.stdout
