import re
import tempfile
from pathlib import Path

import typer
from typer.testing import CliRunner

from drudgeyer.cli.add import main as add_main
from drudgeyer.cli.delete import main
from drudgeyer.cli.show import main as list_main

app = typer.Typer()
app.command("delete")(main)
app.command("add")(add_main)
app.command("list")(list_main)

runner = CliRunner()


def test_delete(mocker):
    with tempfile.TemporaryDirectory() as tempdir:
        mocker.patch("drudgeyer.cli.add.BASEDIR", Path(tempdir))
        mocker.patch("drudgeyer.cli.show.BASEDIR", Path(tempdir))
        mocker.patch("drudgeyer.cli.delete.BASEDIR", Path(tempdir))

        # add test task
        result = runner.invoke(app, ["add", "echo 2"])
        result = runner.invoke(app, ["add", "echo 3"])
        assert result.exit_code == 0, result.stdout

        # query task ids
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0, result.stdout

        assert len(result.stdout.split("\n")) > 2, result.stdout

        parsed = re.findall(r"\([0-9\-]+\)", result.stdout)
        parsed = [f.strip("()") for f in parsed]

        # delete task
        target = parsed[-1]
        result = runner.invoke(app, ["delete", target])
        assert result.exit_code == 0, result.stdout

        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0, result.stdout
        parsed = re.findall(r"\([0-9\-]+\)", result.stdout)
        parsed = [f.strip("()") for f in parsed]
        assert target not in parsed

        # with dependencies
        with tempfile.TemporaryDirectory() as tempsrcdir:
            srcdir = Path(tempsrcdir)
            (srcdir / "a.txt").touch()
            result = runner.invoke(app, ["echo 111", "-d", tempsrcdir])

            # query task ids
            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0, result.stdout

            assert len(result.stdout.split("\n")) > 2, result.stdout

            parsed = re.findall(r"\([0-9\-]+\)", result.stdout)
            parsed = [f.strip("()") for f in parsed]

            # delete task
            target = parsed[-1]
            result = runner.invoke(app, ["delete", target])
            assert result.exit_code == 0, result.stdout

            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0, result.stdout
            parsed = re.findall(r"\([0-9\-]+\)", result.stdout)
            parsed = [f.strip("()") for f in parsed]
            assert target not in parsed
            assert not (Path(tempdir) / "dep" / target).is_dir()


def test_delete_failed(mocker):
    with tempfile.TemporaryDirectory() as tempdir:
        mocker.patch("drudgeyer.cli.delete.BASEDIR", Path(tempdir))
        result = runner.invoke(app, ["delete", ""])
        assert result.exit_code == 1, result.stdout

    with tempfile.TemporaryDirectory() as tempdir:
        mocker.patch("drudgeyer.cli.delete.BASEDIR", Path(tempdir))
        result = runner.invoke(app, ["delete", "x"])
        assert result.exit_code == 1, result.stdout
