import asyncio
import logging
import signal
from abc import ABC, abstractmethod
from asyncio.events import AbstractEventLoop
from asyncio.queues import Queue
from dataclasses import dataclass
from pathlib import Path
from types import FrameType
from typing import AsyncGenerator, Callable, Dict, List, Optional, Set

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from uvicorn import Config, Server  # type: ignore

from drudgeyer.log_tracker.log_streamer import (
    BaseLogStreamer,
    QueueFileHandler,
    QueueHandler,
)


class BaseReadStreamer(ABC):
    """streaming log data from queue handler in log_streamer"""

    @abstractmethod
    async def get(self, key: str) -> str:
        ...  # pragma: no cover

    @abstractmethod
    async def add_client(self, id: str, key: str) -> None:
        ...  # pragma: no cover

    @abstractmethod
    async def delete(self, key: str) -> None:
        ...  # pragma: no cover


@dataclass
class ReadQueue:
    """Queue each client for broadcasting"""

    key: str
    target: str
    queue: "Queue[str]"
    live: bool = True


@dataclass
class LogQueue:
    """Queue streaming log data from LogStreamer"""

    id: str
    targets: Set[str]
    queue: "Queue[str]"
    live: bool = True
    task: Optional["asyncio.Task[None]"] = None


class LocalReadStreamer(BaseReadStreamer):
    """streaming log data from queue handler in log_streamer"""

    def __init__(
        self, log_streamer: BaseLogStreamer, loop: Optional[AbstractEventLoop] = None
    ):
        handler: Optional[QueueHandler] = None
        _file: Optional[QueueFileHandler] = None

        for _handler in log_streamer._handlers:
            if isinstance(_handler, QueueHandler):
                handler = _handler
            if isinstance(_handler, QueueFileHandler):
                _file = _handler
        if handler is None:
            raise ValueError("QueueHandler is not found")
        self.handler = handler
        self._file = _file

        self._key_to_readqueue: Dict[str, ReadQueue] = {}
        self._id_to_logqueue: Dict[str, LogQueue] = {}
        self._loop = loop if loop else asyncio.get_event_loop()

    def _reflesh(self) -> None:
        for log_queue in self._id_to_logqueue.values():
            if not log_queue.live and log_queue.task is not None:
                try:
                    if not log_queue.task.cancelled():
                        log_queue.task.cancel()
                except asyncio.CancelledError:
                    pass

    async def entry_point(self, log_queue: LogQueue) -> None:
        # possibly bottle neck
        queue = log_queue.queue
        try:
            while log_queue.live:
                log = await queue.get()
                keys = log_queue.targets
                for key in keys:
                    _queue = self._key_to_readqueue.get(key)
                    if _queue and _queue.live:
                        await _queue.queue.put(log)
        except (RuntimeError, asyncio.CancelledError):
            # queue is deleted
            log_queue.live = False
            self._reflesh()

    async def get(self, key: str) -> str:
        queue = self._key_to_readqueue.get(key)
        if not queue:
            raise KeyError("must add key at first")
        if not queue.live:
            raise ValueError("broken connection. try again")
        try:
            log = await queue.queue.get()
            return log
        except (RuntimeError, asyncio.CancelledError):
            queue.live = False
        raise ValueError("broken connection. try again")

    async def add_client(self, id: str, key: str) -> None:
        # create if none
        read = self._key_to_readqueue.get(key)
        if read and read.target == id and read.live:
            pass
        else:
            _queue: Queue[str] = Queue()
            if self._file:
                _record = await self._file.get_record(id)
                if _record:
                    await _queue.put(_record)
                    await _queue.put("-------------- loading -------------\n")

            read = ReadQueue(key=key, target=id, queue=_queue)
            self._key_to_readqueue[key] = read

        # create if none
        log = self._id_to_logqueue.get(id)
        if log and log.live:
            log.targets.add(key)
        else:
            await self.handler.add(id)
            handler_queues = self.handler._queues
            queue = handler_queues.get(id)
            if queue:
                log = LogQueue(
                    id=id,
                    targets={key},
                    queue=queue,
                )
                self._id_to_logqueue[id] = log
                loop = asyncio.get_event_loop()
                log.task = loop.create_task(self.entry_point(log))
        self._reflesh()

    async def delete(self, key: str) -> None:
        # delete ReadQueue
        read = self._key_to_readqueue.get(key)
        if read:
            read.live = False
            try:
                del self._key_to_readqueue[key]
            except KeyError:
                pass
        # cancel sync task and delete LogQueue
        new_id_to_logqueue = {}
        for log in self._id_to_logqueue.values():
            if {key} == log.targets:
                await self.handler.delete(log.id)
                log.targets = set([])
                log.live = False
                if log.task:
                    log.task.cancel()
            else:
                new_id_to_logqueue[log.id] = log
        self._reflesh()


class GetReadStreamer:
    """Helper class for streaming log data for broadcasting with websocket"""

    def __init__(self, key: str, streamer: BaseReadStreamer, ws: WebSocket):
        self._streamer = streamer
        self._key = key
        self._ws = ws
        self.exit = False

    async def streaming(self) -> None:
        try:
            while not self.exit:
                log = await self._streamer.get(self._key)
                await self._ws.send_text(log)
        except (Exception, WebSocketDisconnect, asyncio.CancelledError):
            pass

    def manual_exit(self) -> None:
        self.exit = True


class Command(BaseModel):
    cmd: str


def streamer(
    read_streamer: BaseReadStreamer,
) -> Callable[[WebSocket, str], AsyncGenerator[GetReadStreamer, None]]:
    async def _streamer(
        ws: WebSocket, id: str
    ) -> AsyncGenerator[GetReadStreamer, None]:
        """Dependency function for ReadStreamer."""
        # prepare streamer
        await ws.accept()
        key = ws.headers.get("sec-websocket-key")
        await read_streamer.add_client(id, key)

        get_read_streamer = GetReadStreamer(key, read_streamer, ws)

        try:
            # start broadcasting
            yield get_read_streamer
        finally:
            # cleanup streamer
            await read_streamer.delete(key)

    return _streamer


class PruneIDs(BaseModel):
    ids: List[str]


def create_app(read_streamer: BaseReadStreamer) -> FastAPI:
    app = FastAPI()

    @app.post("/add-task")
    async def add_task(body: Command) -> None:
        path = Path("storage/queue")
        with path.open("a+") as f:
            f.write(body.cmd)

    def get_filehandler() -> Optional[QueueFileHandler]:
        if isinstance(read_streamer, LocalReadStreamer):
            filehandler = read_streamer._file
            return filehandler
        return None

    @app.post("/log-trace/prune")
    async def log_tracker_prune(
        body: PruneIDs,
        file_handler: Optional[QueueFileHandler] = Depends(get_filehandler),
    ) -> None:
        if file_handler and body.ids:
            await asyncio.gather(*[file_handler.delete(id) for id in body.ids])

    @app.websocket("/log-trace")
    async def log_tracker(
        ws: WebSocket,
        streamer: GetReadStreamer = Depends(streamer(read_streamer)),
    ) -> None:
        loop = asyncio.get_event_loop()
        task = loop.create_task(streamer.streaming())

        try:
            while True:
                await ws.receive()
        except (Exception, WebSocketDisconnect):
            streamer.manual_exit()
            task.cancel()
            await ws.close()

    return app


def run_receiver(
    app: FastAPI,
    event_loop: asyncio.AbstractEventLoop,
    handlers: List[Callable[[signal.Signals, Optional[FrameType]], None]],
) -> Server:
    """
    NOTE: Uvicorn override signal handler for eventloop in the case of "ctrl-c" and "kill pid".
    So, tasks in eventloop other than "Uvicorn" cannot exit if "ctrl-c" and "kill pid".
    To solve it, inject signal handler for other tasks.
    """

    class SubServer(Server):  # type: ignore
        def handle_exit(self, sig: signal.Signals, frame: Optional[FrameType]) -> None:
            super().handle_exit(sig, frame)
            for handler in handlers:
                handler(sig, frame)

    config = Config(app=app, loop=event_loop, log_level=logging.ERROR)

    server = SubServer(config)
    return server
