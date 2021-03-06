from pathlib import Path
from typing import Optional

import typer

from drudgeyer.cli import BASEDIR
from drudgeyer.job_scheduler.dependency import CopyDep
from drudgeyer.job_scheduler.queue import QUEUE_CLASSES, Queues


def main(
    command: str = typer.Argument(..., help="execution command"),
    directory: Optional[Path] = typer.Option(
        None, "-d", "--dir", help="directory for dependencies"
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

    dep = CopyDep(directory, BASEDIR / "dep")
    queue_ = QUEUE_CLASSES[queue](path=BASEDIR / "queue", depends=dep)

    item = queue_.enqueue(command)
    typer.secho(
        f"Queued:\n- Order: {item.order}\n- ID: {item.id}\n- Command: {item.command}\n- Workdir: {item.workdir}",
        fg=typer.colors.CYAN,
    )
