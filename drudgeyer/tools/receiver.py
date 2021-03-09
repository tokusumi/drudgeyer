import asyncio
import logging
import signal
from abc import ABC, abstractmethod
from asyncio.events import AbstractEventLoop
from asyncio.queues import Queue
from dataclasses import dataclass
from pathlib import Path
from types import FrameType
from typing import AsyncGenerator, Callable, Dict, List, Optional

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from uvicorn import Config, Server  # type: ignore

from drudgeyer.tools.log_streamer import BaseLogStreamer, QueueHandler


class BaseReadStreamer(ABC):
    @abstractmethod
    async def get(self, key: str) -> str:
        ...

    @abstractmethod
    async def add_client(self, id: str, key: str) -> None:
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        ...


@dataclass
class ReadQueue:
    """Queue for each client in application"""

    key: str
    target: str
    queue: "Queue[str]"
    live: bool = True


@dataclass
class LogQueue:
    """Queue in LogStreamer"""

    id: str
    targets: List[str]
    queue: "Queue[str]"
    live: bool = True


class LocalReadStremaer(BaseReadStreamer):
    def __init__(
        self, log_streamer: BaseLogStreamer, loop: Optional[AbstractEventLoop] = None
    ):
        handler: Optional[QueueHandler] = None
        for _handler in log_streamer._handlers:
            if isinstance(_handler, QueueHandler):
                handler = _handler
        if handler is None:
            raise ValueError("QueueHandler is not found")
        self.handler = handler
        self._key_to_id: Dict[str, str] = {}
        self._id_to_keys: Dict[str, List[str]] = {}
        self._key_to_readqueue: Dict[str, ReadQueue] = {}
        self._id_to_logqueue: Dict[str, LogQueue] = {}
        self._loop = loop if loop else asyncio.get_event_loop()

    def _reflesh(self) -> None:
        key_to_id = {}
        id_to_keys = {}
        for read in self._key_to_readqueue.values():
            if read.live:
                target_log_queue = self._id_to_logqueue.get(read.target)
                if target_log_queue:
                    target_log_queue.targets.append(read.key)
        for log_queue in self._id_to_logqueue.values():
            if log_queue.live:
                living_read_queues = []
                for key in log_queue.targets:
                    read_queue = self._key_to_readqueue.get(key)
                    if read_queue and read_queue.live:
                        living_read_queues.append(key)
                        key_to_id[key] = log_queue.id
                id_to_keys[log_queue.id] = living_read_queues

                if log_queue.id not in self._id_to_keys:
                    loop = asyncio.get_event_loop()
                    loop.create_task(self.entry_point(log_queue))

        self._key_to_id = key_to_id
        self._id_to_keys = id_to_keys

    async def entry_point(self, log_queue: LogQueue) -> None:
        # possibly bottle neck
        id = log_queue.id
        queue = log_queue.queue
        while log_queue.live:
            try:
                log = await queue.get()
                await asyncio.sleep(0.1)
                log_queue.live = False
            except RuntimeError:
                # queue is deleted
                log_queue.live = False
                self._reflesh()
                break
            keys = self._id_to_keys.get(id)
            if keys:
                for key in keys:
                    _queue = self._key_to_readqueue.get(key)
                    if _queue and _queue.live:
                        await _queue.queue.put(log)

    async def get(self, key: str) -> str:
        queue = self._key_to_readqueue.get(key)
        if not queue:
            raise KeyError("must add key at first")
        if not queue.live:
            raise ValueError("broken connection. try again")
        try:
            log = await queue.queue.get()
            return log
        except RuntimeError:
            queue.live = False
        raise ValueError("broken connection. try again")

    async def add_client(self, id: str, key: str) -> None:
        read = self._key_to_readqueue.get(key)
        if read and read.target == id and read.live:
            pass
        else:
            read = ReadQueue(key=key, target=id, queue=Queue())
            self._key_to_readqueue[key] = read

        log = self._id_to_logqueue.get(id)
        if log and log.live:
            pass
        else:
            await self.handler.add(id)
            handler_queues = self.handler._queues
            queue = handler_queues.get(id)
            if queue:
                log = LogQueue(id=id, targets=[], queue=queue)
                self._id_to_logqueue[id] = log
        self._reflesh()

    async def delete(self, key: str) -> None:
        try:
            read = self._key_to_readqueue.get(key)
            if read:
                read.live = False
                del self._key_to_readqueue[key]
            for log in self._id_to_logqueue.values():
                if not log.live:
                    await self.handler.delete(log.id)
            self._reflesh()

        except KeyError:
            pass


class GetReadStreamer:
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
        except (Exception, WebSocketDisconnect):
            pass
        await self._ws.close()

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
        await ws.accept()
        key = ws.headers.get("sec-websocket-key")
        await read_streamer.add_client(id, key)

        get_read_streamer = GetReadStreamer(key, read_streamer, ws)

        try:
            yield get_read_streamer
        finally:
            await read_streamer.delete(key)

    return _streamer


def create_app(read_streamer: BaseReadStreamer) -> FastAPI:
    app = FastAPI()

    @app.post("/add-task")
    async def add_task(body: Command) -> None:
        path = Path("storage/queue")
        with path.open("a+") as f:
            f.write(body.cmd)

    @app.websocket("/log-trace")
    async def log_tracker(
        ws: WebSocket,
        streamer: GetReadStreamer = Depends(streamer(read_streamer)),
    ) -> None:
        loop = asyncio.get_event_loop()
        loop.create_task(streamer.streaming())

        try:
            while True:
                await ws.receive()
        except (Exception, WebSocketDisconnect):
            streamer.manual_exit()
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
