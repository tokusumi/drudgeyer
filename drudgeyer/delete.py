from pathlib import Path

import typer

from drudgeyer.tools.queue import QUEUE_CLASSES, Queues


def main(
    id: str = typer.Argument(..., help="Unique ID of target"),
    directory: Path = typer.Option(
        Path("./"), "-d", "--dir", help="directory for dependencies"
    ),
    queue: Queues = typer.Option("file", "-q", help="select queue"),
) -> None:
    """Delete job queue via http connection
    For:
    - on-premise: Delete current job queue using Queue directly
    - cloud (future): send string of command and zip file of dependencies
    """
    queue_ = QUEUE_CLASSES[queue](directory)
    try:
        queue_.pop(id)
    except FileNotFoundError:
        typer.secho("Invalid ID", fg=typer.colors.RED)
        raise typer.Abort()

    typer.secho(f"Delete queue: {id}", fg=typer.colors.CYAN)
