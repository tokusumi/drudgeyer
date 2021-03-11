import asyncio

import typer
import websockets


async def entry_point(uri: str) -> None:
    try:
        async with websockets.connect(uri) as websocket:
            async for msg in websocket:
                typer.echo(msg)
    except websockets.ConnectionClosedError:
        typer.secho("Connection closed", fg=typer.colors.RED)
    except OSError:
        typer.secho("not found", fg=typer.colors.RED)
    except Exception as e:
        typer.secho(str(e), fg=typer.colors.RED)


def main(
    id: str = typer.Argument(..., help="check task id using drudgeyer list"),
    url: str = typer.Argument(..., help="log-tracker server URL"),
) -> None:
    """Application: tracking task logs from log-tracker application
    For:
    - on-premise: Access with Queue directly
    - cloud (future): send string of command and zip file of dependencies
    """
    url = f"ws://{url}/log-trace?id={id}"
    loop = asyncio.get_event_loop()
    loop.run_until_complete(entry_point(url))
    raise typer.Exit(1)
