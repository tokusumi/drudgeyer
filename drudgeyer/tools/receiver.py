import asyncio
from pathlib import Path
from typing import Any, Coroutine

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


def run_receiver(event_loop: asyncio.AbstractEventLoop) -> Coroutine[Any, Any, Any]:
    config = Config(app=app, loop=event_loop)
    server = Server(config)
    return server.serve()
