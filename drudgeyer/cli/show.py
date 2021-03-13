import typer

from drudgeyer.cli import BASEDIR
from drudgeyer.job_scheduler.dependency import CopyDep
from drudgeyer.job_scheduler.queue import QUEUE_CLASSES, Queues


def main(
    queue: Queues = typer.Option("file", "-q", help="select queue"),
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

    typer.secho("Current Queue: ", fg=typer.colors.CYAN)

    for item in items:
        typer.echo(f"{item.order}: ({item.id}) {item.command} in {item.workdir}")
