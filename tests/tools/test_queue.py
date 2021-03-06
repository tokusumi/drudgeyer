import tempfile
from pathlib import Path
from time import sleep
from typing import List

import pytest

from drudgeyer.tools.queue import BaseQueueModel, FileQueue


def assert_items(expected: List[str], items: List[BaseQueueModel]) -> bool:
    assert len(items) == len(expected)
    for idx, (o, cmd) in enumerate(zip(items, expected)):
        assert o.command == cmd
        assert o.order == idx
    return True


def test_filequeue():
    with tempfile.TemporaryDirectory() as f:
        path = Path(f) / "xxx"
        queue = FileQueue(path.resolve())

        # add items
        expected_items = ["cmd3", "cmd2", "cmd4"]
        for cmd in expected_items:
            queue.enqueue(cmd)
            sleep(0.01)

        # show all items in queue
        out = queue.list()
        assert assert_items(expected_items, out)

        # pop first item
        first = queue.dequeue()
        expected_items = ["cmd2", "cmd4"]
        out = queue.list()
        assert first.command == "cmd3", out
        assert assert_items(expected_items, out)

        # pop specific order item
        target = out[-1].id
        queue.pop(target)
        expected_items = ["cmd2"]
        out = queue.list()
        assert assert_items(expected_items, out)

        # empty-queue case
        queue.dequeue()
        empty = queue.dequeue()
        assert not empty

        empty = queue.list()
        assert not empty

        with pytest.raises(FileNotFoundError):
            queue.pop("aaaaa")
