import asyncio
from abc import ABC, abstractmethod
from asyncio.subprocess import PIPE, STDOUT, create_subprocess_shell
from signal import Signals
from types import FrameType
from typing import Any, Optional

from drudgeyer.tools.logger import BaseLog
from drudgeyer.tools.queue import BaseQueue, BaseQueueModel


class BaseWorker(ABC):
    def __init__(self, freq: float = 1):
        self.freq = freq
        self.should_exit: bool = False
        self.force_exit: bool = False

    async def _run(self, loop: asyncio.AbstractEventLoop) -> None:
        try:
            while not self.should_exit:
                task = await self.dequeue()
                if self.should_exit:
                    return
                if task:
                    await self.run(task, loop)
                else:
                    await asyncio.sleep(self.freq)

                if not self.should_exit:
                    await asyncio.sleep(self.freq)
        except asyncio.CancelledError as e:
            return

    @abstractmethod
    async def dequeue(self) -> BaseQueueModel:
        ...

    @abstractmethod
    async def run(self, task: BaseQueueModel, loop: asyncio.AbstractEventLoop) -> None:
        ...

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

    async def dequeue(self) -> Any:
        return self._queue.dequeue()

    async def run(self, task: BaseQueueModel, loop: asyncio.AbstractEventLoop) -> None:
        # TODO: add safe terminate process for subprocess shell
        self._logger.reset(task.id, task.command)

        if self.should_exit:
            return

        command = task.command
        try:
            process = await create_subprocess_shell(
                command,
                stdout=PIPE,
                stderr=STDOUT,
                loop=loop,
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
