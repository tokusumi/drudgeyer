import asyncio
from abc import ABC, abstractmethod
from asyncio.subprocess import PIPE, STDOUT, create_subprocess_shell
from signal import Signals
from types import FrameType
from typing import Any, Optional

from drudgeyer.job_scheduler.queue import BaseQueue, BaseQueueModel, Status
from drudgeyer.worker.logger import BaseLog


class BaseWorker(ABC):
    def __init__(self, freq: float = 1):
        self.freq = freq
        self.should_exit: bool = False
        self.force_exit: bool = False

    # fmt: off
    @abstractmethod
    async def dequeue(self) -> Optional[BaseQueueModel]: ...  # pragma: no cover
    @abstractmethod
    async def worked(self, task: BaseQueueModel, status: Status) -> None: ...  # pragma: no cover
    @abstractmethod
    async def run(self, task: BaseQueueModel, loop: asyncio.AbstractEventLoop) -> Status: ...  # pragma: no cover
    # fmt: on

    async def _run(self, loop: asyncio.AbstractEventLoop) -> None:
        try:
            while not self.should_exit:
                task = await self.dequeue()
                if self.should_exit:
                    return
                if task:
                    status = await self.run(task, loop)
                    await self.worked(task, status)
                else:
                    await asyncio.sleep(self.freq)
        except asyncio.CancelledError:
            return

    def handle_exit(self, sig: Signals, frame: Optional[FrameType]) -> None:
        if self.should_exit:
            self.force_exit = True
        else:
            self.should_exit = True


class Worker(BaseWorker):
    def __init__(
        self, logger: BaseLog, queue: BaseQueue, *args: Any, **kwargs: Any
    ) -> None:
        self._logger = logger
        self._queue = queue
        super().__init__(*args, **kwargs)

    async def dequeue(self) -> Optional[BaseQueueModel]:
        return self._queue.dequeue()

    async def worked(self, task: BaseQueueModel, status: Status) -> None:
        self._queue.worked(task.id, status)

    async def run(
        self, task: BaseQueueModel, loop: asyncio.AbstractEventLoop
    ) -> Status:
        # TODO: add safe terminate process for subprocess shell
        self._logger.reset(task.id, task.command)

        if self.should_exit:
            return Status.failed

        command = task.command
        cwd = task.workdir
        try:
            process = await create_subprocess_shell(
                command, stdout=PIPE, stderr=STDOUT, loop=loop, cwd=cwd
            )
            if process.stdout:
                asyncio.create_task(self._logger._output(process.stdout))

            exitcode = await process.wait()  # 0 means success

        except (OSError, FileNotFoundError, PermissionError) as exception:
            self._logger.exception(exception)
            exitcode = 1
        else:
            # no exception was raised
            self._logger.finish()

        if exitcode == 0:
            # success
            return Status.done

        return Status.failed
