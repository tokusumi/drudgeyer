import asyncio
import logging
import logging.handlers
import sys
from abc import ABC, abstractmethod
from asyncio.events import AbstractEventLoop
from asyncio.queues import Queue as aQueue
from enum import Enum
from pathlib import Path
from queue import SimpleQueue as Queue
from typing import Any, Callable, Dict, List, Optional, Type

from pydantic.main import BaseModel


class LogModel(BaseModel):
    id: str
    log: str


async def readuntil(self: asyncio.StreamReader, separator: bytes = b"\n") -> bytes:
    """Read data from the stream until ``separator`` is found."""
    separators = [separator, b"\r"]
    seplen = len(separator)
    if seplen == 0:
        raise ValueError("Separator should be at least one-byte string")

    if self._exception is not None:  # type: ignore
        raise self._exception  # type: ignore

    offset = 0
    # Loop until we find `separator` in the buffer, exceed the buffer size,
    # or an EOF has happened.
    while True:
        buflen = len(self._buffer)  # type: ignore

        # Check if we now have enough data in the buffer for `separator` to
        # fit.
        if buflen - offset >= seplen:
            for sep in separators:
                isep = self._buffer.find(sep, offset)  # type: ignore

                if isep != -1:
                    # `separator` is in the buffer. `isep` will be used later
                    # to retrieve the data.
                    break

            if isep != -1:
                break

            # see upper comment for explanation.
            offset = buflen + 1 - seplen
            if offset > self._limit:  # type: ignore
                raise asyncio.LimitOverrunError(
                    "Separator is not found, and chunk exceed the limit", offset
                )

        # Complete message (with full separator) may be present in buffer
        # even when EOF flag is set. This may happen when the last chunk
        # adds data which makes separator be found. That's why we check for
        # EOF *ater* inspecting the buffer.
        if self._eof:  # type: ignore
            chunk = bytes(self._buffer)  # type: ignore
            self._buffer.clear()  # type: ignore
            raise asyncio.IncompleteReadError(chunk, None)

        # _wait_for_data() will resume reading if stream was paused.
        await self._wait_for_data("readuntil")  # type: ignore

    if isep > self._limit:  # type: ignore
        raise asyncio.LimitOverrunError(
            "Separator is found, but chunk is longer than limit", isep
        )

    chunk = self._buffer[: isep + seplen]  # type: ignore
    del self._buffer[: isep + seplen]  # type: ignore
    self._maybe_resume_transport()  # type: ignore
    return bytes(chunk)


async def readline(self: asyncio.StreamReader) -> bytes:
    sep = b"\n"
    seplen = len(sep)
    try:
        line = await readuntil(self, sep)
    except asyncio.IncompleteReadError as e:
        return e.partial
    except asyncio.LimitOverrunError as e:
        if self._buffer.startswith(sep, e.consumed):  # type: ignore
            del self._buffer[: e.consumed + seplen]  # type: ignore
        else:
            self._buffer.clear()  # type: ignore
        self._maybe_resume_transport()  # type: ignore
        raise ValueError(e.args[0])
    return line


class BaseLog(ABC):
    @property
    @abstractmethod
    def log(self) -> Callable[[str], Any]:
        ...  # pragma: no cover

    def reset(self, id: str, command: str) -> None:
        self.log('\nTask: "' + command + '"\n')

    def output(self, input: bytes) -> None:
        if input:
            self.log(input.decode())

    async def _output(self, pipe: asyncio.StreamReader) -> None:
        while not pipe.at_eof():
            line = await readline(pipe)
            self.output(line)

    def exception(self, exception: BaseException) -> None:
        self.log("Exception occured: %s\n" % exception)
        self.log("Task failed\n")

    def finish(self) -> None:
        self.log("Task finished\n")


class PrintLogger(BaseLog):
    def __init__(self) -> None:
        self._log = sys.stdout.write

    @property
    def log(self) -> Callable[[str], Any]:
        return self._log


class LocalQueueHandler(logging.handlers.QueueHandler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.enqueue(record)
        except asyncio.CancelledError:
            raise
        except Exception:
            self.handleError(record)


class QueueFileLogger(BaseLog):
    @property
    def log(self) -> Callable[[str], Any]:
        return self._log

    def reset(self, id: str, command: str, logdir: str = "log") -> None:
        self.set_handler(id, logdir=logdir)
        self._setup_logging_queue(id)
        self.logger = logging.getLogger(id)
        self._log = self.logger.info
        super().reset(id, command)

    def set_handler(self, id: str, logdir: str = "log") -> None:
        logger = logging.getLogger(id)
        logger.setLevel(logging.INFO)

        path = Path(logdir)
        path.mkdir(exist_ok=True)
        path = path / id
        path.touch(exist_ok=False)
        handler = logging.FileHandler(path.resolve())
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    def _setup_logging_queue(self, id: str) -> None:
        """Move log handlers to a separate thread"""
        handlers: List[logging.Handler] = []
        queue: Queue[logging.LogRecord] = Queue()
        handler = LocalQueueHandler(queue)

        logger = logging.getLogger(id)
        logger.addHandler(handler)
        for h in logger.handlers[:]:
            if h is not handler:
                logger.removeHandler(h)
                handlers.append(h)

        listener = logging.handlers.QueueListener(
            queue, *handlers, respect_handler_level=True
        )
        listener.start()


class StreamingLogger(BaseLog):
    def __init__(
        self, maxsize: int = 1000, loop: Optional[AbstractEventLoop] = None
    ) -> None:
        self._log: aQueue[LogModel] = aQueue(maxsize, loop=loop)

    def reset(self, id: str, command: str) -> None:
        def log(command: str) -> None:
            self._log.put_nowait(LogModel(id=id, log=command))

        self._logfunc = log

    @property
    def log(self) -> Callable[[str], Any]:
        return self._logfunc

    async def dequeue(self) -> LogModel:
        log = await self._log.get()
        self._log.task_done()
        return log


class Loggers(Enum):
    console = "console"
    log = "log"
    stream = "stream"


LOGGER_CLASSES: Dict[Loggers, Type[BaseLog]] = {
    Loggers.console: PrintLogger,
    Loggers.log: QueueFileLogger,
    Loggers.stream: StreamingLogger,
}
