import tempfile
from pathlib import Path
from unittest import mock

import typer
from typer.testing import CliRunner

from drudgeyer.cli.add import main as add_main
from drudgeyer.cli.show import main
from drudgeyer.job_scheduler.queue import BaseQueueModel, Status

app = typer.Typer()
app.command("list")(main)
app.command("add")(add_main)

runner = CliRunner()


def test_list(mocker: mock):
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

    # mock requests
    with tempfile.TemporaryDirectory() as tempdir:
        mocker.patch("drudgeyer.cli.add.BASEDIR", Path(tempdir))
        mocker.patch("drudgeyer.cli.show.BASEDIR", Path(tempdir))
        result = runner.invoke(app, ["add", "echo 1"])
        result = runner.invoke(app, ["add", "echo 2"])
        assert result.exit_code == 0, result.stdout

        mocker.patch("requests.post", lambda x, y, headers: None)
        result = runner.invoke(app, ["list", "--prune"])
        assert result.exit_code == 0, result.stdout

    # successfully show items
    with tempfile.TemporaryDirectory() as tempdir:
        mocker.patch("drudgeyer.cli.show.BASEDIR", Path(tempdir))
        mocker.patch(
            "drudgeyer.job_scheduler.queue.FileQueue.list",
            lambda x: [
                BaseQueueModel(id="xxx0", order=0, command="", status=Status.todo),
                BaseQueueModel(id="xxx1", order=1, command="", status=Status.doing),
                BaseQueueModel(id="xxx2", order=2, command="", status=Status.done),
                BaseQueueModel(id="xxx3", order=3, command="", status=Status.failed),
            ],
        )

        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0, result.stdout

        assert len(result.stdout.split("\n")) > 4, result.stdout
