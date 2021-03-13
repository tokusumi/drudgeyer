import tempfile
from pathlib import Path

import typer
from typer.testing import CliRunner

from drudgeyer.cli.add import main as add_main
from drudgeyer.cli.show import main

app = typer.Typer()
app.command("list")(main)
app.command("add")(add_main)

runner = CliRunner()


def test_list(mocker):
    # no item, no error
    with tempfile.TemporaryDirectory() as tempdir:
        mocker.patch("drudgeyer.cli.show.BASEDIR", Path(tempdir))
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0, result.stdout

    # successfully query items
    with tempfile.TemporaryDirectory() as tempdir:
        mocker.patch("drudgeyer.cli.add.BASEDIR", Path(tempdir))
        mocker.patch("drudgeyer.cli.show.BASEDIR", Path(tempdir))
        result = runner.invoke(app, ["add", "echo 1"])
        result = runner.invoke(app, ["add", "echo 2"])
        assert result.exit_code == 0, result.stdout

        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0, result.stdout

        assert len(result.stdout.split("\n")) > 2, result.stdout
