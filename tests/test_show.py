import tempfile

import typer
from typer.testing import CliRunner

from drudgeyer.add import main as add_main
from drudgeyer.show import main

app = typer.Typer()
app.command("list")(main)
app.command("add")(add_main)

runner = CliRunner()


def test_list():
    # no item, no error
    with tempfile.TemporaryDirectory() as tempdir:
        result = runner.invoke(app, ["list", "-d", tempdir])
        assert result.exit_code == 0, result.stdout

    # successfully query items
    with tempfile.TemporaryDirectory() as tempdir:
        result = runner.invoke(app, ["add", "'echo 1'", "-d", tempdir])
        result = runner.invoke(app, ["add", "'echo 2'", "-d", tempdir])
        assert result.exit_code == 0, result.stdout

        result = runner.invoke(app, ["list", "-d", tempdir])
        assert result.exit_code == 0, result.stdout

        assert len(result.stdout.split("\n")) > 2, result.stdout
