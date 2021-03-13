import asyncio
import os
import tempfile
import threading
import time
from asyncio.events import AbstractEventLoop
from pathlib import Path
from signal import SIGINT

import pytest
import typer
from typer.testing import CliRunner

from drudgeyer.cli.run import main

app = typer.Typer()
app.command()(main)

runner = CliRunner()


def lazy_fire_terminate_signal(lazy: float = 1) -> None:
    """send terminate signal after time "lazy"
    NOTE: usecase:
    - run and stop infinite loop function in the test
    - testing error handling when function is terminated
    """
    pid = os.getpid()

    def trigger_signal():
        time.sleep(lazy)
        os.kill(pid, SIGINT)

    thread = threading.Thread(target=trigger_signal)
    thread.start()


async def dummy_inf_loop(time: float) -> None:
    """dummy asyncronous infinite loop function"""
    await asyncio.sleep(time)


def test_lazy_fire_signal():
    with pytest.raises(KeyboardInterrupt):
        # raise KeyboardInterrupt after 0.01 sec
        lazy_fire_terminate_signal(0.01)

        # dummy main heavy process
        time.sleep(0.5)


@pytest.mark.timeout(5)
def test_override_signal(event_loop: AbstractEventLoop) -> None:
    # hack signal handler as terminate will be ignored
    event_loop.add_signal_handler(SIGINT, lambda sig, frame: ..., SIGINT, None)

    lazy_fire_terminate_signal(0.1)
    # asynchronous dummy heavy process will be terminated 0.1 sec later
    event_loop.run_until_complete(dummy_inf_loop(0.3))

    # terminate was ignored. successfully main process finished


@pytest.mark.timeout(0.05)
@pytest.mark.xfail
def test_override_signal_but_timeout_works(event_loop: AbstractEventLoop) -> None:
    # check timeout works or not
    event_loop.add_signal_handler(SIGINT, lambda sig, frame: ..., SIGINT, None)
    lazy_fire_terminate_signal(0.1)
    event_loop.run_until_complete(dummy_inf_loop(0.3))


@pytest.mark.timeout(20)
def test_run(mocker):
    """For testing ctrl-c successfully works for the app
    NOTE: this test will be automatically failed 20 sec later,
    because main process is infinite loop.
    """
    # ctrl-c will be sent to terminate main process 5 sec later
    lazy_fire_terminate_signal(5)

    with tempfile.TemporaryDirectory() as tempdir:
        mocker.patch("drudgeyer.cli.run.BASEDIR", Path(tempdir))

        # running main process (inspect queue, handle worker and ...)
        result = runner.invoke(app, [])
        assert result.exit_code == 0, result.stdout
