import typer

from drudgeyer.cli import add, delete, log, run, show

app = typer.Typer()
app.command("run")(run.main)
app.command("add")(add.main)
app.command("list")(show.main)
app.command("delete")(delete.main)
app.command("log")(log.main)


@app.callback()
def callback() -> None:
    """Job Queue Tools"""
