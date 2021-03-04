import asyncio
from abc import ABC, abstractmethod
from asyncio.subprocess import PIPE, STDOUT, create_subprocess_shell
from typing import Any

from drudgeyer.tools.logger import BaseLog
from drudgeyer.tools.queue import BaseQueue


class BaseWorker(ABC):
    def __init__(self, freq: float = 1):
        self.freq = freq

    async def _run(self, loop: asyncio.AbstractEventLoop) -> None:
        while True:
            task = await self.dequeue()
            if task:
                await self.run(task, loop)
            else:
                await asyncio.sleep(self.freq)
            await asyncio.sleep(self.freq)

    @abstractmethod
    async def dequeue(self) -> Any:
        ...

    @abstractmethod
    async def run(self, task: Any, loop: asyncio.AbstractEventLoop) -> None:
        ...


async def run_shell_command(
    command: str, logger: BaseLog, loop: asyncio.AbstractEventLoop
) -> int:
    try:
        process = await create_subprocess_shell(
            command,
            stdout=PIPE,
            stderr=STDOUT,
            loop=loop,
        )
        if process.stdout:
            asyncio.create_task(logger._output(process.stdout))

        exitcode = await process.wait()  # 0 means success

    except (OSError, FileNotFoundError, PermissionError) as exception:
        logger.exception(exception)
        return 1
    else:
        # no exception was raised
        logger.finish()

    return exitcode


class Worker(BaseWorker):
    def __init__(
        self, logger: BaseLog, queue: BaseQueue, *args: Any, **kwargs: Any
    ) -> None:
        self._logger = logger
        self._queue = queue
        super().__init__(*args, **kwargs)

    async def dequeue(self) -> Any:
        return self._queue.dequeue()

    async def run(self, task: str, loop: asyncio.AbstractEventLoop) -> None:
        self._logger.intro(task)
        await run_shell_command(task, self._logger, loop)
