import os
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

        # with dependencies
        with tempfile.TemporaryDirectory() as tempsrcdir:
            srcdir = Path(tempsrcdir)
            (srcdir / "a.txt").touch()
            result = runner.invoke(app, ["echo 111", "-d", tempsrcdir])

            assert result.exit_code == 0, result.stdout
            id = os.listdir(Path(tempdir) / "dep")[0]
            assert (Path(tempdir) / "dep" / id / srcdir.name / "a.txt").is_file()


def test_add_failed(mocker):
    with tempfile.TemporaryDirectory() as tempdir:
        mocker.patch("drudgeyer.cli.add.BASEDIR", Path(tempdir))
        result = runner.invoke(app, [""])
        assert result.exit_code == 1, result.stdout
