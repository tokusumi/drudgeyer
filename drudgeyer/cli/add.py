from pathlib import Path

import typer

from drudgeyer.job_scheduler.dependency import CopyDep
from drudgeyer.job_scheduler.queue import QUEUE_CLASSES, Queues


def main(
    command: str = typer.Argument(..., help="execution command"),
    directory: Path = typer.Option(
        Path("./src"), "-d", "--dir", help="directory for dependencies"
    ),
    queue: Queues = typer.Option("file", "-q", help="select queue"),
) -> None:
    """Applicatin: Pass new job into Queue
    For:
    - on-premise: Access with Queue directly
    - cloud (future): send string of command and zip file of dependencies
    """
    if not command:
        typer.secho("Invalid command", fg=typer.colors.RED)
        raise typer.Abort()

    basedir = Path(".drudgeyer")

    dep = CopyDep(directory, basedir / "dep")
    queue_ = QUEUE_CLASSES[queue](path=basedir / "queue", depends=dep)

    queue_.enqueue(command)
    typer.secho(f"Queued: {command}", fg=typer.colors.CYAN)
