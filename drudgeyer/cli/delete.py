from pathlib import Path

import typer

from drudgeyer.job_scheduler.dependency import CopyDep
from drudgeyer.job_scheduler.queue import QUEUE_CLASSES, Queues


def main(
    id: str = typer.Argument(..., help="Unique target ID"),
    queue: Queues = typer.Option("file", "-q", help="select queue"),
) -> None:
    """Application: Delete job Queue
    For:
    - on-premise: Access with Queue directly
    - cloud (future): send string of command and zip file of dependencies
    """
    basedir = Path(".drudgeyer")

    dep = CopyDep(None, basedir / "dep")
    queue_ = QUEUE_CLASSES[queue](path=basedir / "queue", depends=dep)
    try:
        queue_.pop(id)
    except FileNotFoundError:
        typer.secho("Invalid ID", fg=typer.colors.RED)
        raise typer.Abort()

    typer.secho(f"Delete queue: {id}", fg=typer.colors.CYAN)
