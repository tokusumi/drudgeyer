import tempfile
from pathlib import Path

import typer
from typer.testing import CliRunner

from drudgeyer.cli.add import main

app = typer.Typer()
app.command()(main)
runner = CliRunner()


def test_add(mocker):
    with tempfile.TemporaryDirectory() as tempdir:
        mocker.patch("drudgeyer.cli.add.BASEDIR", Path(tempdir))
        result = runner.invoke(app, ["echo 111"])
        assert result.exit_code == 0, result.stdout


def test_add_failed(mocker):
    with tempfile.TemporaryDirectory() as tempdir:
        mocker.patch("drudgeyer.cli.add.BASEDIR", Path(tempdir))
        result = runner.invoke(app, [""])
        assert result.exit_code == 1, result.stdout
