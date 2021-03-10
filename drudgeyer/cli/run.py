import asyncio
from pathlib import Path

import typer

from drudgeyer.job_scheduler.queue import QUEUE_CLASSES, Queues
from drudgeyer.log_tracker import log_streamer
from drudgeyer.log_tracker.broadcasting import (LocalReadStreamer, create_app,
                                                run_receiver)
from drudgeyer.worker.logger import LOGGER_CLASSES, Loggers, StreamingLogger
from drudgeyer.worker.shell import Worker


def main(
    http: bool = typer.Option(True, "-h", help="connect via http"),
    directory: Path = typer.Option(
        Path("./storage"), "-d", "--dir", help="directory for dependencies"
    ),
    queue: Queues = typer.Option("file", "-q", help="select queue"),
    logger: Loggers = typer.Option("stream", "-l", help="select logger"),
    streamer: log_streamer.LogStreamers = typer.Option(
        "local", "-s", help="select log streamer"
    ),
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
        log_streamer_handler = log_streamer.QueueHandler()
        log_streamer_class = log_streamer.LOGSTREAMER_CLASSES[streamer]
        if log_streamer_class == log_streamer.LocalLogStreamer and isinstance(
            logger_, StreamingLogger
        ):
            log_streamer_ = log_streamer.LocalLogStreamer(
                [log_streamer.QueueFileHandler(), log_streamer_handler], logger_
            )
            read_streamer = LocalReadStreamer(log_streamer_)

            app = create_app(read_streamer)
            server = run_receiver(
                app, loop, [worker.handle_exit, log_streamer_.handle_exit]
            )
            loop.create_task(server.serve())
            loop.create_task(log_streamer_.entry_point())

    try:
        loop.run_until_complete(worker._run(loop))
    except KeyboardInterrupt:
        pass
