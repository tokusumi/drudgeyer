import tempfile

import typer
from typer.testing import CliRunner

from drudgeyer.add import main

app = typer.Typer()
app.command()(main)

runner = CliRunner()


def test_add():
    with tempfile.TemporaryDirectory() as tempdir:
        result = runner.invoke(app, ["'echo 111'", "-d", tempdir])
        assert result.exit_code == 0, result.stdout


def test_add_failed():
    result = runner.invoke(app, [""])
    assert result.exit_code == 1, result.stdout
