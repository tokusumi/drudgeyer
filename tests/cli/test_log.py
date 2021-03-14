from typing import AsyncIterator

import pytest
import typer
import websockets
from typer.testing import CliRunner
from websockets.typing import Data

from drudgeyer.cli.log import entry_point, main

app = typer.Typer()
app.command()(main)

runner = CliRunner()


@pytest.mark.timeout(0.1)
def test_not_found():
    id = "xxx"
    uri = "example..com"
    result = runner.invoke(app, [id, uri])
    assert result.exit_code == 1, result.stdout


class DummyWebSocketClientProtcol:
    def __init__(self, resp: str, repeat: int = 2, exception: Exception = None):
        self._resp = resp
        self._repeat = repeat
        self._exception = exception

    def __await__(self):
        yield
        return self

    def __aenter__(self):
        return self

    async def __aexit__(self, *args, **kwargs):
        await self.close()

    async def __aiter__(self) -> AsyncIterator[Data]:
        for _ in range(self._repeat):
            yield self._resp
        if self._exception:
            raise self._exception

    async def close(self, *args, **kwargs):
        pass


@pytest.mark.asyncio
async def test_websockets_mock(mocker, capsys):
    websocket = mocker.patch("websockets.connect")
    dummy_resp = "test\n"
    repeat = 2
    websocket.return_value = DummyWebSocketClientProtcol(dummy_resp, repeat)
    await entry_point("")
    captured = capsys.readouterr()
    assert captured.out == "test\ntest\n"


@pytest.mark.asyncio
async def test_websockets_closed(mocker, capsys):
    websocket = mocker.patch("websockets.connect")
    dummy_resp = "test\n"
    repeat = 0
    exception = websockets.ConnectionClosedError(1008, "")
    websocket.return_value = DummyWebSocketClientProtcol(dummy_resp, repeat, exception)
    await entry_point("")
    captured = capsys.readouterr()
    assert captured.out == "Connection closed\n"


@pytest.mark.asyncio
async def test_websockets_not_found(mocker, capsys):
    websocket = mocker.patch("websockets.connect")
    dummy_resp = "test\n"
    repeat = 0
    exception = OSError
    websocket.return_value = DummyWebSocketClientProtcol(dummy_resp, repeat, exception)
    await entry_point("")
    captured = capsys.readouterr()
    assert captured.out == "not found\n"


@pytest.mark.asyncio
async def test_websockets_exception(mocker):
    websocket = mocker.patch("websockets.connect")
    dummy_resp = "test\n"
    repeat = 0
    exception = Exception
    websocket.return_value = DummyWebSocketClientProtcol(dummy_resp, repeat, exception)
    await entry_point("")
