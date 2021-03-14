import asyncio
import tempfile
from asyncio.events import AbstractEventLoop
from asyncio.subprocess import PIPE, STDOUT
from pathlib import Path
from time import sleep

import pytest

from drudgeyer.worker import logger


def test_print(capsys):
    logger_ = logger.PrintLogger()
    logger_.log("test")
    captured = capsys.readouterr()
    assert captured.out == "test"


def test_filelogger():
    logger_ = logger.QueueFileLogger()
    with tempfile.TemporaryDirectory() as f:
        path = Path(f)
        logger_.reset("xxx-test-file-logger", "xxx", logdir=path.resolve())
        logger_.log("test")

        log = path / "xxx-test-file-logger"
        sleep(0.1)
        with log.open() as f:
            assert "test\n" == f.readlines()[-1]


def test_streaminglogger(event_loop: AbstractEventLoop) -> None:
    logger_ = logger.StreamingLogger()
    logger_.reset("xxx", "yyy")
    logger_.log("test")

    async def assert_logger(logger_: logger.StreamingLogger) -> None:
        log = await logger_.dequeue()
        assert log.log == "test"
        assert log.id == "xxx"

    event_loop.run_until_complete(assert_logger(logger_))


@pytest.mark.asyncio
async def test_readuntil(mocker) -> None:
    loop = asyncio.get_event_loop()
    process = await asyncio.create_subprocess_shell(
        "echo 111111", stdout=PIPE, stderr=STDOUT, loop=loop, limit=1
    )
    with pytest.raises(ValueError):
        await logger.readuntil(process.stdout, b"")

    with pytest.raises(asyncio.LimitOverrunError):
        await logger.readuntil(process.stdout, b"\n")

    await process.wait()  # 0 means success

    process = await asyncio.create_subprocess_shell(
        'echo -e "\n"', stdout=PIPE, stderr=STDOUT, loop=loop, limit=1
    )
    with pytest.raises(asyncio.LimitOverrunError):
        await logger.readuntil(process.stdout, b"\n")

    await process.wait()  # 0 means success

    process = await asyncio.create_subprocess_shell(
        'echo -e "\n"', stdout=PIPE, stderr=STDOUT, loop=loop, limit=1
    )
    with pytest.raises(ValueError):
        await logger.readline(process.stdout)
    await logger.readline(process.stdout)
    await process.wait()  # 0 means success
