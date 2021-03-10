import asyncio
import logging
import logging.handlers
import sys
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from queue import SimpleQueue as Queue
from typing import Any, Callable, Dict, List, Type


class BaseLog(ABC):
    @property
    @abstractmethod
    def log(self) -> Callable[[str], Any]:
        ...

    def reset(self, id: str, command: str) -> None:
        self.log('\nTask: "' + command + '"\n')

    def output(self, input: bytes) -> None:
        if input:
            self.log(input.decode())

    async def _output(self, pipe: asyncio.StreamReader) -> None:
        while not pipe.at_eof():
            line = await pipe.readline()
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
        self._setup_logging_queue()
        self.logger = logging.getLogger()
        self._log = self.logger.info
        super().reset(id, command)

    def set_handler(self, id: str, logdir: str = "log") -> None:
        root = logging.getLogger()
        root.setLevel(logging.INFO)

        path = Path(logdir) / id
        path.touch(exist_ok=True)
        handler = logging.FileHandler(path.resolve())
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        root.addHandler(handler)

    def _setup_logging_queue(self) -> None:
        """Move log handlers to a separate thread"""
        handlers: List[logging.Handler] = []
        queue: Queue[logging.LogRecord] = Queue()
        handler = LocalQueueHandler(queue)

        root = logging.getLogger()
        root.addHandler(handler)
        for h in root.handlers[:]:
            if h is not handler:
                root.removeHandler(h)
                handlers.append(h)

        listener = logging.handlers.QueueListener(
            queue, *handlers, respect_handler_level=True
        )
        listener.start()


class Loggers(Enum):
    console = "console"
    log = "log"


LOGGER_CLASSES: Dict[Loggers, Type[BaseLog]] = {
    Loggers.console: PrintLogger,
    Loggers.log: QueueFileLogger,
}
