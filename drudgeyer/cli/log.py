import asyncio

import aiohttp
import typer


async def entry_point(url: str) -> None:
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(url) as ws:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    if msg.data == "close cmd":
                        await ws.close()
                        return
                    else:
                        typer.echo(msg.data)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    return


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
