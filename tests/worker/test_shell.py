import asyncio
from asyncio.events import AbstractEventLoop
from signal import SIGINT
from typing import Any, Callable, Optional, Type

import pytest

from drudgeyer.job_scheduler.queue import BaseQueueModel, Status
from drudgeyer.worker.logger import BaseLog
from drudgeyer.worker.shell import BaseWorker, Worker


class ValidDequeueTerminateRun(BaseWorker):
    async def dequeue(self) -> BaseQueueModel:
        assert not self.should_exit
        return BaseQueueModel(order=0, command="echo 1", id="11-11")

    async def worked(self, task: BaseQueueModel, status: Status) -> None:
        return None  # pragma: no cover

    async def run(self, task: BaseQueueModel, loop: AbstractEventLoop) -> None:
        assert not self.should_exit
        self.handle_exit(SIGINT, None)


class NullTerminateDequeueNullRun(BaseWorker):
    async def dequeue(self) -> Optional[BaseQueueModel]:
        assert not self.should_exit
        self.handle_exit(SIGINT, None)
        return None

    async def worked(self, task: BaseQueueModel, status: Status) -> None:
        return super().worked(task, status)  # pragma: no cover

    async def run(self, task: BaseQueueModel, loop: AbstractEventLoop) -> None:
        assert not self.should_exit  # pragma: no cover


class ValidTerminateDequeueNullRun(BaseWorker):
    async def dequeue(self) -> BaseQueueModel:
        assert not self.should_exit
        self.handle_exit(SIGINT, None)
        return BaseQueueModel(order=0, command="echo 1", id="11-11")

    async def worked(self, task: BaseQueueModel, status: Status) -> None:
        return super().worked(task, status)  # pragma: no cover

    async def run(self, task: BaseQueueModel, loop: AbstractEventLoop) -> None:
        assert not self.should_exit  # pragma: no cover


@pytest.mark.timeout(0.5)
@pytest.mark.parametrize(
    "_base",
    [
        NullTerminateDequeueNullRun,
        ValidTerminateDequeueNullRun,
        ValidDequeueTerminateRun,
    ],
)
def test_handle_exit(
    event_loop: AbstractEventLoop,
    _base: Type[BaseWorker],
) -> None:
    # In "_run", if terminated (called handle_exit) once in a method,
    # loop will be soon broken before calling next method
    event_loop.run_until_complete(_base(freq=0.01)._run(event_loop))

    # no loop if handle_exit has been already called
    base = _base(freq=0.01)
    base.handle_exit(SIGINT, None)
    base.handle_exit(SIGINT, None)
    event_loop.run_until_complete(base._run(event_loop))


class DummyLogger(BaseLog):
    @property
    def log(self) -> Callable[[str], Any]:
        return print


@pytest.mark.asyncio
async def test_exec_command() -> None:
    loop = asyncio.get_event_loop()
    worker = Worker(logger=DummyLogger(), queue=None)  # type: ignore

    # success
    task = BaseQueueModel(id="111-111", command="echo 1", order=0)
    status = await worker.run(task, loop)
    assert status == Status.done

    # failure
    task = BaseQueueModel(id="111-111", command="python3 -c 'print())'", order=0)
    status = await worker.run(task, loop)
    assert status == Status.failed
