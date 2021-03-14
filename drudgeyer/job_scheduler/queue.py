import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Type

from pydantic import BaseModel

from drudgeyer.job_scheduler.dependency import BaseDep


class BaseQueueModel(BaseModel):
    id: str
    order: int
    command: str
    workdir: Path = Path("")


if TYPE_CHECKING:
    from typing import TypeVar

    QueueModel = TypeVar("QueueModel", bound="BaseQueueModel")


class BaseQueue(ABC):
    # fmt: off
    def __init__(self, path: Path, depends: BaseDep) -> None: ...  # pragma: no cover
    @abstractmethod
    def dequeue(self) -> Optional[BaseQueueModel]: ...  # pragma: no cover
    @abstractmethod
    def enqueue(self, cmd: str) -> BaseQueueModel: ...  # pragma: no cover
    @abstractmethod
    def list(self) -> List[BaseQueueModel]: ...  # pragma: no cover
    @abstractmethod
    def pop(self, id: str) -> None: ...  # pragma: no cover
    # fmt: on


class FileQueue(BaseQueue):
    def __init__(
        self, path: Path = Path("storage"), depends: Optional[BaseDep] = None
    ) -> None:
        self.path = path
        self.done = path / "done"

        if not path.is_dir():
            path.mkdir(parents=True, exist_ok=True)

        if not self.done.is_dir():
            self.done.mkdir(parents=True, exist_ok=True)

        self.depends = depends

    def enqueue(self, cmd: str) -> BaseQueueModel:
        now = datetime.now()
        id = now.strftime("%Y-%m-%d-%H-%M-%S-%f")
        file = self.path / id
        if file.is_file():
            self.enqueue(cmd)

        if self.depends:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.depends.dump(id))
            workdir = self.depends.workdir(id)
        else:
            workdir = Path("")

        with file.open("w") as f:
            f.write(cmd)

        order = len(list(file.glob("*-*-*-*-*-*-*")))

        return BaseQueueModel(id=id, command=cmd, order=order, workdir=workdir)

    def dequeue(self) -> Optional[BaseQueueModel]:
        files = list(self.path.glob("*-*-*-*-*-*-*"))
        if not files:
            return None

        times = [datetime.strptime(f.name, "%Y-%m-%d-%H-%M-%S-%f") for f in files]
        minn: datetime = times[0]
        minn_idx = 0
        for idx, time in enumerate(times):
            if time < minn:
                minn = time
                minn_idx = idx
        target = files[minn_idx]
        with target.open() as f:
            cmd = f.read()
        target.rename(self.done.resolve() / target.name)

        if self.depends:
            workdir = self.depends.workdir(target.name)
        else:
            workdir = Path("")
        return BaseQueueModel(id=target.name, command=cmd, order=0, workdir=workdir)

    def list(self) -> List[BaseQueueModel]:
        files = list(self.path.glob("*-*-*-*-*-*-*"))
        if not files:
            return []

        times = [
            (idx, datetime.strptime(f.name, "%Y-%m-%d-%H-%M-%S-%f"))
            for idx, f in enumerate(files)
        ]
        times.sort(key=lambda x: x[1])
        out = []
        for order, (idx, file) in enumerate(times):
            target = files[idx]
            if self.depends:
                workdir = self.depends.workdir(target.name)
            else:
                workdir = Path("")
            with target.open() as f:
                out.append(
                    BaseQueueModel(
                        id=target.name, order=order, command=f.read(), workdir=workdir
                    )
                )
        return out

    def pop(self, id: str) -> None:
        target = self.path / id
        if not target.is_file():
            raise FileNotFoundError
        target.unlink()
        if self.depends:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.depends.clear(id))


class Queues(Enum):
    file = "file"
    redis = "redis"
    db = "db"


QUEUE_CLASSES: Dict[Queues, Type[BaseQueue]] = {Queues.file: FileQueue}
