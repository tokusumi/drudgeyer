import tempfile
from pathlib import Path
from time import sleep
from typing import List

import pytest

from drudgeyer.job_scheduler.dependency import BaseDep
from drudgeyer.job_scheduler.queue import BaseQueueModel, FileQueue, Status


def assert_items(expected: List[str], items: List[BaseQueueModel]) -> bool:
    assert len(items) == len(expected)
    for idx, (o, cmd) in enumerate(zip(items, expected)):
        assert o.command == cmd
        assert o.order == idx
    return True


class NullDep(BaseDep):
    def __init__(self, path: Path = Path("dep")) -> None:
        self._path = path / "dep"
        if not self._path.is_dir():
            self._path.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path  # pragma: no cover

    async def dump(self, id: str) -> None:
        return

    def workdir(self, id: str) -> Path:
        return Path("")

    async def clear(self, id: str) -> None:
        return


@pytest.mark.parametrize("_depends", [None, NullDep])
def test_filequeue(_depends):
    with tempfile.TemporaryDirectory() as f:
        rootdir = Path(f)
        path = rootdir / "xxx"
        if _depends:
            _depends = _depends(rootdir)
        queue = FileQueue(path=path.resolve(), depends=_depends)

        # add items
        expected_items = ["cmd3", "cmd2", "cmd4"]
        for cmd in expected_items:
            queue.enqueue(cmd)
            sleep(0.01)

        # show all items in queue
        out = queue.list(detail=True)
        assert assert_items(expected_items, out)

        # pop first item
        first = queue.dequeue()
        expected_items = ["cmd2", "cmd4"]
        out = queue.list(detail=True, status=Status.todo)
        assert first.command == "cmd3", out
        assert assert_items(expected_items, out)

        # pop specific order item
        target = out[-1].id
        queue.pop(target)
        expected_items = ["cmd2"]
        out = queue.list(detail=True, status=Status.todo)
        assert assert_items(expected_items, out)

        # empty-queue case
        queue.dequeue()
        empty = queue.dequeue()
        assert not empty

        empty = queue.list(detail=True, status=Status.todo)
        assert not empty

        with pytest.raises(FileNotFoundError):
            queue.pop("aaaaa")


@pytest.mark.parametrize("_depends", [None, NullDep])
def test_filequeue_status(_depends):
    with tempfile.TemporaryDirectory() as f:
        rootdir = Path(f)
        path = rootdir / "xxx"
        if _depends:
            _depends = _depends(rootdir)
        queue = FileQueue(path=path.resolve(), depends=_depends)

        # add items
        expected_items = ["cmd1", "cmd2", "cmd3", "cmd4"]
        for cmd in expected_items:
            queue.enqueue(cmd)
            sleep(0.01)

        # prepare done task (cmd1)
        out = queue.dequeue()
        queue.worked(out.id, Status.done)
        assert queue.list(detail=True, status=Status.done)[0].command == "cmd1"
        assert queue.list(detail=False, status=Status.done)[0].command == ""

        # prepare failed task (cmd2)
        out = queue.dequeue()
        queue.worked(out.id, Status.failed)
        assert queue.list(detail=True, status=Status.failed)[0].command == "cmd2"
        assert queue.list(detail=False, status=Status.failed)[0].command == ""

        # prepare todo task (cmd3)
        out = queue.dequeue()
        assert queue.list(detail=True, status=Status.doing)[0].command == "cmd3"
        assert queue.list(detail=False, status=Status.doing)[0].command == ""

        # check last task (cmd4)
        assert queue.list(detail=True, status=Status.todo)[0].command == "cmd4"
        assert queue.list(detail=False, status=Status.todo)[0].command == ""

        # show all
        assert len(queue.list()) == 4

        # prune tasks
        queue.prune()
        assert len(queue.list()) == 2
        assert not queue.list(status=Status.done)
        assert not queue.list(status=Status.failed)
