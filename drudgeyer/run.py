import asyncio
from pathlib import Path

import typer

from drudgeyer.tools.logger import LOGGER_CLASSES, Loggers
from drudgeyer.tools.queue import QUEUE_CLASSES, Queues
from drudgeyer.tools.receiver import run_receiver
from drudgeyer.tools.shell import Worker


def main(
    http: bool = typer.Option(True, "-h", help="connect via http"),
    directory: Path = typer.Option(
        Path("./storage"), "-d", "--dir", help="directory for dependencies"
    ),
    queue: Queues = typer.Option("file", "-q", help="select queue"),
    logger: Loggers = typer.Option("console", "-l", help="select logger"),
    frequency: float = typer.Option(
        3, "--freq", help="worker inspection frequency [sec]"
    ),
) -> None:
    """Managements Runner for:
    - Worker: run or wait worker subprocess for the latest job in queue, including logging.
    - Queue: CRUD for Queue (add job, get jobs, ...)
    """

    queue_ = QUEUE_CLASSES[queue](directory)
    logger_ = LOGGER_CLASSES[logger]()

    loop = asyncio.get_event_loop()
    loop.set_debug(False)

    worker = Worker(logger_, queue_, freq=frequency)

    if http:
        server = run_receiver(loop, [worker.handle_exit])
        loop.create_task(server.serve())

    loop.run_until_complete(worker._run(loop))
