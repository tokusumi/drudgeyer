import asyncio
import sys
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Type


class BaseLog(ABC):
    @abstractmethod
    def intro(self, command: str) -> None:
        ...

    @abstractmethod
    def output(self, input: bytes) -> None:
        ...

    async def _output(self, pipe: asyncio.StreamReader) -> None:
        while not pipe.at_eof():
            line = await pipe.readline()
            self.output(line)

    @abstractmethod
    def exception(self, exception: BaseException) -> None:
        ...

    @abstractmethod
    def finish(self) -> None:
        ...


class PrintLogger(BaseLog):
    def intro(self, command: str) -> None:
        sys.stdout.write('\nTask: "' + command + '"\n')

    def output(self, input: bytes) -> None:
        if input:
            sys.stdout.buffer.write(input)

    def exception(self, exception: BaseException) -> None:
        sys.stdout.write("Exception occured: %s\n" % exception)
        sys.stdout.write("Task failed\n")

    def finish(self) -> None:
        sys.stdout.write("Task finished\n")


class Loggers(Enum):
    console = "console"
    log = "log"


LOGGER_CLASSES: Dict[Loggers, Type[BaseLog]] = {Loggers.console: PrintLogger}
