import pytest
import typer
from typer.testing import CliRunner

from drudgeyer.cli.log import main

app = typer.Typer()
app.command()(main)

runner = CliRunner()


@pytest.mark.timeout(0.1)
def test_not_found():
    id = "xxx"
    uri = "111://"
    result = runner.invoke(app, [id, uri])
    assert result.exit_code == 1, result.stdout
