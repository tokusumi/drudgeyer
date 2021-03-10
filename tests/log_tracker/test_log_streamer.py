import asyncio
import tempfile
from asyncio.events import AbstractEventLoop
from pathlib import Path
from signal import SIGINT

import pytest

from drudgeyer.log_tracker import log_streamer
from drudgeyer.worker.logger import LogModel, StreamingLogger


class ToyHandler(log_streamer.BaseHandler):
    def __init__(self) -> None:
        self.cnt = 1

    async def send(self, log: LogModel) -> None:
        for _ in range(self.cnt):
            print(f"toy-{log.log}")

    async def add(self, id: str) -> None:
        self.cnt += 1

    async def delete(self, id: str) -> None:
        self.cnt = 1


class ToyLogStreamer(log_streamer.BaseLogStreamer):
    async def recv(self) -> LogModel:
        return LogModel(id="xxx", log="test")

    async def entry_point(self) -> None:
        ...  # pragma: no cover


def test_baselogstreamer(capsys, event_loop: AbstractEventLoop) -> None:
    event_loop.run_until_complete(ToyLogStreamer([ToyHandler()]).streaming())
    captured = capsys.readouterr()
    assert captured.out == "toy-test\n"

    _streamer = ToyLogStreamer([ToyHandler()])
    _streamer.add("yyy")
    event_loop.run_until_complete(_streamer.streaming())
    captured = capsys.readouterr()
    assert captured.out == "toy-test\ntoy-test\n"

    _streamer = ToyLogStreamer([ToyHandler()])
    # exit mode
    _streamer.handle_exit(SIGINT, None)
    assert _streamer.should_exit and not _streamer.force_exit
    # force exit mode
    _streamer.handle_exit(SIGINT, None)
    assert _streamer.should_exit and _streamer.force_exit


@pytest.mark.timeout(0.5)
def test_locallogstreamer(capsys, event_loop: AbstractEventLoop) -> None:
    logger = StreamingLogger()
    logger.reset("xxx", "yyy")
    streamer = log_streamer.LocalLogStreamer(
        [ToyHandler()],
        logger,
    )

    async def _toy_logging(
        logger: StreamingLogger, streamer: log_streamer.LocalLogStreamer
    ) -> None:
        await asyncio.sleep(0.1)
        # logging by logger
        logger.log("test")
        # log will be sent into streamer, and handler, then printted out
        await asyncio.sleep(0.3)
        streamer.handle_exit(SIGINT, None)

    event_loop.create_task(streamer.entry_point())
    event_loop.run_until_complete(_toy_logging(logger, streamer))
    event_loop.stop()

    captured = capsys.readouterr()
    assert captured.out == "toy-test\n"


async def workflow(handler: log_streamer.BaseHandler) -> None:
    await handler.add("xxx")
    await handler.add("yyy")

    # written in /xxx
    await handler.send(LogModel(id="xxx", log="test-x"))
    # written in /yyy
    await handler.send(LogModel(id="yyy", log="test-y"))
    # invalid id. ignored
    await handler.send(LogModel(id="zzz", log="test-z"))
    await asyncio.sleep(0.3)


def test_queuefilehandler(event_loop: AbstractEventLoop) -> None:
    with tempfile.TemporaryDirectory() as f:
        logdir = Path(f) / "log"
        handler = log_streamer.QueueFileHandler(str(logdir.resolve()))
        event_loop.run_until_complete(workflow(handler))

        with (logdir / "xxx").open() as fx:
            assert fx.read() == "test-x\n"
        with (logdir / "yyy").open() as fy:
            assert fy.read() == "test-y\n"
        assert not (logdir / "zzz").is_file()


def test_queue_handler(event_loop: AbstractEventLoop) -> None:
    handler = log_streamer.QueueHandler()
    event_loop.run_until_complete(workflow(handler))

    queues = handler._queues
    assert queues.get("xxx").get_nowait() == "test-x"
    assert queues.get("yyy").get_nowait() == "test-y"
    assert not queues.get("zzz")
