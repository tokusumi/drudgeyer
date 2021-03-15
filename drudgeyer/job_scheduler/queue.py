import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from shutil import rmtree
from typing import TYPE_CHECKING, Dict, List, Optional, Type

from pydantic import BaseModel

from drudgeyer.job_scheduler.dependency import BaseDep


class Status(Enum):
    todo = auto()
    doing = auto()
    done = auto()
    failed = auto()


class BaseQueueModel(BaseModel):
    id: str
    order: int
    command: str
    workdir: Path = Path("")
    status: Status = Status.todo


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
    def list(self, detail: bool = False, status: Optional[Status] = None) -> List[BaseQueueModel]: ...  # pragma: no cover
    @abstractmethod
    def worked(self, id: str, status: Status) -> None: ...  # pragma: no cover
    @abstractmethod
    def pop(self, id: str) -> None: ...  # pragma: no cover
    @abstractmethod
    def prune(self) -> None: ...  # pragma: no cover
    # fmt: on


class FileQueue(BaseQueue):
    def __init__(
        self, path: Path = Path("storage"), depends: Optional[BaseDep] = None
    ) -> None:
        self.path = path
        self.doing = path / "doing"
        self.done = path / "done"
        self.failed = path / "failed"

        if not path.is_dir():
            path.mkdir(parents=True, exist_ok=True)
        if not self.doing.is_dir():
            self.doing.mkdir(parents=True, exist_ok=True)
        if not self.done.is_dir():
            self.done.mkdir(parents=True, exist_ok=True)
        if not self.failed.is_dir():
            self.failed.mkdir(parents=True, exist_ok=True)

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

        target.rename(self.doing.resolve() / target.name)

        if self.depends:
            workdir = self.depends.workdir(target.name)
        else:
            workdir = Path("")
        return BaseQueueModel(id=target.name, command=cmd, order=0, workdir=workdir)

    def worked(self, id: str, status: Status) -> None:
        target = self.doing / id
        if not target.is_file():
            return

        if status == Status.done:
            target.rename(self.done.resolve() / target.name)
        elif status == Status.failed:
            target.rename(self.failed.resolve() / target.name)
        return

    def _list(
        self,
        files: List[Path],
        status: Status,
        detail: bool = False,
        out: Optional[List[BaseQueueModel]] = None,
    ) -> None:
        times = [
            (idx, datetime.strptime(f.name, "%Y-%m-%d-%H-%M-%S-%f"))
            for idx, f in enumerate(files)
        ]
        times.sort(key=lambda x: x[1])

        if out is None:
            out = []
        out_a = out.append
        for order, (idx, file) in enumerate(times):
            target = files[idx]
            if detail:
                if self.depends:
                    workdir = self.depends.workdir(target.name)
                else:
                    workdir = Path("")
                with target.open() as f:
                    cmd = f.read()
            else:
                workdir = Path("")
                cmd = ""
            out_a(
                BaseQueueModel(
                    id=target.name,
                    order=order,
                    command=cmd,
                    workdir=workdir,
                    status=status,
                )
            )

    def list(
        self, detail: bool = False, status: Optional[Status] = None
    ) -> List[BaseQueueModel]:
        items: List[BaseQueueModel] = []
        # todo
        if status is None or status == Status.todo:
            files = list(self.path.glob("*-*-*-*-*-*-*"))
            if files:
                self._list(files, status=Status.todo, detail=detail, out=items)
        # doing
        if status is None or status == Status.doing:
            files = list(self.doing.glob("*-*-*-*-*-*-*"))
            if files:
                self._list(files, status=Status.doing, detail=detail, out=items)
        # done
        if status is None or status == Status.done:
            files = list(self.done.glob("*-*-*-*-*-*-*"))
            if files:
                self._list(files, status=Status.done, detail=detail, out=items)
        # failed
        if status is None or status == Status.failed:
            files = list(self.failed.glob("*-*-*-*-*-*-*"))
            if files:
                self._list(files, status=Status.failed, detail=detail, out=items)
        return items

    def pop(self, id: str) -> None:
        target = self.path / id
        if not target.is_file():
            raise FileNotFoundError
        target.unlink()
        if self.depends:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.depends.clear(id))

    def prune(self) -> None:
        items = self.list(detail=False, status=Status.done)
        items += self.list(detail=False, status=Status.failed)
        ids = [item.id for item in items if item.status in {Status.done, Status.failed}]
        rmtree(self.failed)
        rmtree(self.done)
        if self.depends and ids:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(
                asyncio.gather(*[self.depends.clear(id) for id in ids])
            )


class Queues(Enum):
    file = "file"
    redis = "redis"
    db = "db"


QUEUE_CLASSES: Dict[Queues, Type[BaseQueue]] = {Queues.file: FileQueue}
