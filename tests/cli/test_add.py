import tempfile

import typer
from typer.testing import CliRunner

from drudgeyer.cli.add import main

app = typer.Typer()
app.command()(main)

runner = CliRunner()


def test_add():
    with tempfile.TemporaryDirectory() as tempdir:
        result = runner.invoke(app, ["'echo 111'", "-d", tempdir])
        assert result.exit_code == 0, result.stdout


def test_add_failed():
    with tempfile.TemporaryDirectory() as tempdir:
        result = runner.invoke(app, ["", "-d", tempdir])
        assert result.exit_code == 1, result.stdout
