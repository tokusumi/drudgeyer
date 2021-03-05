import asyncio
import logging
import signal
from pathlib import Path
from types import FrameType
from typing import Callable, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel
from uvicorn import Config, Server  # type: ignore


class Command(BaseModel):
    cmd: str


app = FastAPI()


@app.post("/add-task")
async def add_task(body: Command) -> None:
    path = Path("storage/queue")
    with path.open("a+") as f:
        f.write(body.cmd)


def run_receiver(
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
