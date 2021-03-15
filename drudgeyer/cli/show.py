import json

import requests
import typer

from drudgeyer.cli import BASEDIR
from drudgeyer.job_scheduler.dependency import CopyDep
from drudgeyer.job_scheduler.queue import QUEUE_CLASSES, Queues, Status


def main(
    prune: bool = typer.Option(False, "--prune", help="delete done, failed records"),
    queue: Queues = typer.Option("file", "-q", help="select queue"),
    url: str = typer.Argument("127.0.0.1:8000", help="log-tracker server URL"),
) -> None:
    """Application: Get current jobs from Queue
    For:
    - on-premise: Access with Queue directly
    - cloud (future): send string of command and zip file of dependencies
    """
    dep = CopyDep(None, BASEDIR / "dep")
    queue_ = QUEUE_CLASSES[queue](path=BASEDIR / "queue", depends=dep)

    items = queue_.list()
    if not items:
        typer.secho("No Queue", fg=typer.colors.GREEN)
        return

    if prune:
        ids = [item.id for item in items if item.status in {Status.done, Status.failed}]
        requests.post(
            f"http://{url}/log-trace/prune",
            json.dumps({"ids": ids}),
            headers={"Content-Type": "application/json"},
        )

        queue_.prune()
        typer.secho("Pruned: done and failed logs", fg=typer.colors.GREEN)
        raise typer.Exit(0)

    # no prune mode
    typer.secho("Current Queue: ", fg=typer.colors.CYAN)

    for item in items:
        if item.status == Status.todo:
            fg = typer.colors.WHITE
            badge = "⏳"
        elif item.status == Status.doing:
            fg = typer.colors.CYAN
            badge = "💨"
        elif item.status == Status.done:
            fg = typer.colors.GREEN
            badge = "✅"
        else:
            fg = typer.colors.RED
            badge = "💥"
        typer.secho(
            f"{badge} {item.order}: ({item.id}) {item.command} in {item.workdir}", fg=fg
        )
