import asyncio
import logging
import logging.handlers
import sys
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from queue import SimpleQueue as Queue
from typing import Dict, List, Type


class BaseLog(ABC):
    @abstractmethod
    def reset(self, id: str, command: str) -> None:
        ...

    @abstractmethod
    def output(self, input: bytes) -> None:
        ...

    async def _output(self, pipe: asyncio.StreamReader) -> None:
        while not pipe.at_eof():
            line = await pipe.readline()
            self.output(line)

    @abstractmethod
    def exception(self, exception: BaseException) -> None:
        ...

    @abstractmethod
    def finish(self) -> None:
        ...


class PrintLogger(BaseLog):
    def reset(self, id: str, command: str) -> None:
        sys.stdout.write('\nTask: "' + command + '"\n')

    def output(self, input: bytes) -> None:
        if input:
            sys.stdout.buffer.write(input)

    def exception(self, exception: BaseException) -> None:
        sys.stdout.write("Exception occured: %s\n" % exception)
        sys.stdout.write("Task failed\n")

    def finish(self) -> None:
        sys.stdout.write("Task finished\n")


class LocalQueueHandler(logging.handlers.QueueHandler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.enqueue(record)
        except asyncio.CancelledError:
            raise
        except Exception:
            self.handleError(record)


class QueueFileLogger(BaseLog):
    def reset(self, id: str, command: str) -> None:
        self.set_handler(id)
        self._setup_logging_queue()
        self.logger = logging.getLogger()
        self.logger.info('Task: "' + command + '"')

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

    def output(self, input: bytes) -> None:
        if input:
            self.logger.info("%s" % input.decode().rstrip("\n"))

    def exception(self, exception: BaseException) -> None:
        self.logger.info("Exception occured: %s" % exception)
        self.logger.info("Task failed")

    def finish(self) -> None:
        self.logger.info("Task finished")


class Loggers(Enum):
    console = "console"
    log = "log"


LOGGER_CLASSES: Dict[Loggers, Type[BaseLog]] = {
    Loggers.console: PrintLogger,
    Loggers.log: QueueFileLogger,
}
