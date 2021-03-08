import tempfile
from asyncio.events import AbstractEventLoop
from pathlib import Path
from time import sleep

from drudgeyer.tools import logger


def test_print(capsys):
    logger_ = logger.PrintLogger()
    logger_.log("test")
    captured = capsys.readouterr()
    assert captured.out == "test"


def test_filelogger():
    logger_ = logger.QueueFileLogger()
    with tempfile.TemporaryDirectory() as f:
        path = Path(f)
        logger_.reset("xxx", "xxx", logdir=path.resolve())
        logger_.log("test")

        log = path / "xxx"
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
