from pathlib import Path

import typer

from drudgeyer.tools.queue import QUEUE_CLASSES, Queues


def main(
    command: str = typer.Argument(..., help="execution command"),
    directory: Path = typer.Option(
        Path("./storage"), "-d", "--dir", help="directory for dependencies"
    ),
    queue: Queues = typer.Option("file", "-q", help="select queue"),
) -> None:
    """Pass new job queue via http connection
    For:
    - on-premise: Pass new job queue using Queue directly
    - cloud (future): send string of command and zip file of dependencies
    """
    queue_ = QUEUE_CLASSES[queue](path=directory)
    if not command:
        typer.secho("Invalid command", fg=typer.colors.RED)
        raise typer.Abort()

    queue_.enqueue(command)
    typer.secho(f"Queued: {command}", fg=typer.colors.CYAN)
