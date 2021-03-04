import typer

from drudgeyer.tools.queue import QUEUE_CLASSES, Queues


def main(
    queue: Queues = typer.Option("file", "-q", help="select queue"),
) -> None:
    """Get current job queue via http connection
    For:
    - on-premise: Get current job queue using Queue directly
    - cloud (future): send string of command and zip file of dependencies
    """
    queue_ = QUEUE_CLASSES[queue]()
    items = queue_.list()
    if not items:
        typer.secho("No Queue", fg=typer.colors.GREEN)
        return

    typer.secho("Current Queue: ", fg=typer.colors.CYAN)

    for item in items:
        typer.echo(f"{item.order}: ({item.id}) {item.command}")
