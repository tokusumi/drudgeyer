import asyncio
import logging
from abc import ABC, abstractmethod
from asyncio.queues import Queue
from enum import Enum
from pathlib import Path
from queue import SimpleQueue
from signal import Signals
from types import FrameType
from typing import Dict, List, Optional, Type

from drudgeyer.worker.logger import LogModel, StreamingLogger


class BaseHandler(ABC):
    """process log streaming data from sub class of BaseLogStreamer
    ex) dump to filesystem, send to broadcasting system and ...
    """

    @abstractmethod
    async def send(self, log: LogModel) -> None:
        ...  # pragma: no cover

    @abstractmethod
    async def add(self, id: str) -> None:
        ...  # pragma: no cover

    @abstractmethod
    async def delete(self, id: str) -> None:
        ...  # pragma: no cover


class BaseLogStreamer(ABC):
    """streaming log data from worker into handlers"""

    def __init__(self, handlers: List[BaseHandler]) -> None:
        self._handlers = handlers
        self.should_exit = False
        self.force_exit = False

    @abstractmethod
    async def recv(self) -> LogModel:
        ...  # pragma: no cover

    @abstractmethod
    async def entry_point(self) -> None:
        ...  # pragma: no cover

    async def streaming(self) -> None:
        """streaming flow in a cycle.
        helper method for entry_point
        """
        log = await self.recv()
        self.send(log)

    def send(self, log: LogModel) -> None:
        asyncio.ensure_future(
            asyncio.gather(*[handler.send(log) for handler in self._handlers])
        )

    def add(self, id: str) -> None:
        asyncio.ensure_future(
            asyncio.gather(*[handler.add(id) for handler in self._handlers])
        )

    def delete(self, id: str) -> None:
        asyncio.ensure_future(
            asyncio.gather(*[handler.delete(id) for handler in self._handlers])
        )

    def handle_exit(self, sig: Signals, frame: Optional[FrameType]) -> None:
        if self.should_exit:
            self.force_exit = True
        else:
            self.should_exit = True


class LocalLogStreamer(BaseLogStreamer):
    """streaming log data from worker into handlers"""

    def __init__(self, handlers: List[BaseHandler], logger: StreamingLogger) -> None:
        self._handlers = handlers
        self._logger = logger
        self.should_exit = False
        self.force_exit = False

    async def entry_point(self) -> None:
        # call add method directly if you want to add new handler
        try:
            while not self.should_exit:
                await self.streaming()
        except (asyncio.CancelledError, RuntimeError):
            return

    async def recv(self) -> LogModel:
        log = await self._logger.dequeue()
        return log


class LogStreamers(Enum):
    local = "local"


LOGSTREAMER_CLASSES: Dict[LogStreamers, Type[BaseLogStreamer]] = {
    LogStreamers.local: LocalLogStreamer,
}


class LocalQueueHandler(logging.handlers.QueueHandler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.enqueue(record)
        except asyncio.CancelledError:
            raise
        except Exception:
            self.handleError(record)


class QueueFileHandler(BaseHandler):
    """save log streaming data in file from sub class of BaseLogStreamer"""

    def __init__(self, logdir: str = "log") -> None:
        self.logdir = logdir
        _logdir = Path(logdir)
        if not _logdir.is_dir():
            _logdir.mkdir(parents=True, exist_ok=True)

        self.loggers: Dict[str, logging.Logger] = {}

    async def send(self, log: LogModel) -> None:
        logger = self.loggers.get(log.id)
        if not logger:
            await self.add(log.id)
            logger = self.loggers.get(log.id)

        if logger:
            logger.info(log.log)

    async def add(self, id: str) -> None:
        if self.loggers.get(id):
            return

        self.set_handler(id, logdir=self.logdir)
        self._setup_logging_queue(id)
        self.loggers[id] = logging.getLogger(id)

    async def delete(self, id: str) -> None:
        pass

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
        queue: SimpleQueue[logging.LogRecord] = SimpleQueue()
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


class QueueHandler(BaseHandler):
    """queue log streaming data from sub class of BaseLogStreamer"""

    def __init__(self) -> None:
        self._queues: Dict[str, Queue[str]] = {}

    async def send(self, log: LogModel) -> None:
        _queue = self._queues.get(log.id)
        if _queue:
            await _queue.put(log.log)

    async def add(self, id: str) -> None:
        if not self._queues.get(id):
            self._queues[id] = Queue()

    async def delete(self, id: str) -> None:
        try:
            del self._queues[id]
        except KeyError:
            pass
