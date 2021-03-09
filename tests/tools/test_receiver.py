import asyncio
from asyncio import AbstractEventLoop

import pytest
from fastapi.testclient import TestClient

from drudgeyer.tools import log_streamer
from drudgeyer.tools.logger import LogModel
from drudgeyer.tools.receiver import LocalReadStremaer, create_app


class ToyLogStreamer(log_streamer.BaseLogStreamer):
    async def recv(self) -> LogModel:
        return LogModel(id="xxx", log="test")

    async def entry_point(self) -> None:
        ...  # pragma: no cover


@pytest.mark.timeout(1)
def test_localread_streamer(event_loop: AbstractEventLoop) -> None:
    async def flow():
        logstreamer = ToyLogStreamer([log_streamer.QueueHandler()])
        read_streamer = LocalReadStremaer(logstreamer)

        id = "xxx"
        key = "key-something"
        # add pipe between log streamer and application read streamer
        await read_streamer.add_client(id, key)
        assert read_streamer._id_to_keys.get(id)
        assert read_streamer._key_to_id.get(key)

        # log streamer receive log and send it into queue for read streamer
        await logstreamer.streaming()

        # read streamer is collectting streaming data asynchronously

        # read streamer get log
        out = await read_streamer.get(key)
        assert out == "test"

        # finish streaming
        await read_streamer.delete(key)

        with pytest.raises(KeyError):
            # can't get data anymore
            await read_streamer.get(key)

    event_loop.run_until_complete(flow())
    event_loop.close()


@pytest.mark.timeout(1)
def test_catch_broken_queue_error(event_loop: AbstractEventLoop) -> None:
    """test for deleting log queue when read queue is awaiting streaming data from log queue"""
    logstreamer = ToyLogStreamer([log_streamer.QueueHandler()])
    read_streamer = LocalReadStremaer(logstreamer)

    async def flow(read_streamer):
        id = "xxx"
        key = "key-something"
        # add pipe between log streamer and application read streamer
        await read_streamer.add_client(id, key)
        assert read_streamer._id_to_keys.get(id)
        assert read_streamer._key_to_id.get(key)

        with pytest.raises(ValueError):
            # keep awaitting to read streamer get log until timeout
            await read_streamer.get(key)

            # successfully raise error and break all running asynchronous process

    async def post_flow(logstreamer):
        await asyncio.sleep(0.3)
        # force delete log queue
        logstreamer.delete("xxx")
        await asyncio.sleep(0.3)

    event_loop.create_task(flow(read_streamer))
    event_loop.run_until_complete(post_flow(logstreamer))
    event_loop.close()


@pytest.mark.timeout(1)
def test_log_trace() -> None:
    logstreamer = ToyLogStreamer([log_streamer.QueueHandler()])
    read_streamer = LocalReadStremaer(logstreamer)
    app = create_app(read_streamer)

    async def flow(logstreamer: ToyLogStreamer):
        # log streamer receive log and send it into queue for read streamer
        logstreamer.add("xxx")
        await logstreamer.streaming()
        await logstreamer.streaming()

    client = TestClient(app)
    with client.websocket_connect("/log-trace?id=xxx") as websocket:
        # running app new event loop in subthread
        subloop: AbstractEventLoop = websocket._loop

        # inject coroutine that streaming log data and wait to finish
        future = asyncio.run_coroutine_threadsafe(flow(logstreamer), subloop)
        future.result()

        # successfully log tracked
        data = websocket.receive_text()
        assert data == "test"
        websocket.close()
    # socket is closed and queues in log streamer and read streamer
    assert not logstreamer._handlers[0]._queues
    assert not read_streamer._key_to_readqueue
