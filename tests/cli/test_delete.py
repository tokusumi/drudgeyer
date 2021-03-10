import re
import tempfile

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


def test_delete():
    with tempfile.TemporaryDirectory() as tempdir:
        # add test task
        result = runner.invoke(app, ["add", "'echo 2'", "-d", tempdir])
        result = runner.invoke(app, ["add", "'echo 3'", "-d", tempdir])
        assert result.exit_code == 0, result.stdout

        # query task ids
        result = runner.invoke(app, ["list", "-d", tempdir])
        assert result.exit_code == 0, result.stdout

        assert len(result.stdout.split("\n")) > 2, result.stdout

        parsed = re.findall(r"\([0-9\-]+\)", result.stdout)
        parsed = [f.strip("()") for f in parsed]

        # delete task
        target = parsed[-1]
        result = runner.invoke(app, ["delete", target, "-d", tempdir])
        assert result.exit_code == 0, result.stdout

        result = runner.invoke(app, ["list", "-d", tempdir])
        assert result.exit_code == 0, result.stdout
        parsed = re.findall(r"\([0-9\-]+\)", result.stdout)
        parsed = [f.strip("()") for f in parsed]
        assert target not in parsed


def test_delete_failed():
    with tempfile.TemporaryDirectory() as tempdir:
        result = runner.invoke(app, ["delete", "", "-d", tempdir])
        assert result.exit_code == 1, result.stdout

    with tempfile.TemporaryDirectory() as tempdir:
        result = runner.invoke(app, ["delete", "x", "-d", tempdir])
        assert result.exit_code == 1, result.stdout
