import asyncio

import typer

from drudgeyer.tools.logger import LOGGER_CLASSES, Loggers
from drudgeyer.tools.queue import QUEUE_CLASSES, Queues
from drudgeyer.tools.receiver import run_receiver
from drudgeyer.tools.shell import Worker


def main(
    http: bool = typer.Option(True, "-h", help="connect via http"),
    queue: Queues = typer.Option("file", "-q", help="select queue"),
    logger: Loggers = typer.Option("console", "-l", help="select logger"),
    frequency: float = typer.Option(
        3, "--freq", help="worker inspection frequency [sec]"
    ),
) -> None:
    """Run daemon threads as follows:
    - worker: run and wait subprocess for the latest job in queue, including logging.
    - receiver: CRUD for Queue (receive job, get jobs, ...)
    """

    queue_ = QUEUE_CLASSES[queue]()
    logger_ = LOGGER_CLASSES[logger]()

    try:
        loop = asyncio.get_event_loop()
        if http:
            loop.create_task(run_receiver(loop))
        loop.run_until_complete(Worker(logger_, queue_, freq=frequency)._run(loop))
    except KeyboardInterrupt:
        loop.close()
        return
