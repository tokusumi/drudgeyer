from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Type

from pydantic import BaseModel


class BaseQueueModel(BaseModel):
    id: str
    order: int
    command: str


if TYPE_CHECKING:
    from typing import TypeVar

    QueueModel = TypeVar("QueueModel", bound="BaseQueueModel")


class BaseQueue(ABC):
    # fmt: off
    def __init__(self, path: Path) -> None: ...  # pragma: no cover
    @abstractmethod
    def dequeue(self) -> Optional[BaseQueueModel]: ...  # pragma: no cover
    @abstractmethod
    def enqueue(self, cmd: str) -> None: ...  # pragma: no cover
    @abstractmethod
    def list(self) -> List[BaseQueueModel]: ...  # pragma: no cover
    @abstractmethod
    def pop(self, id: str) -> None: ...  # pragma: no cover
    # fmt: on


class FileQueue(BaseQueue):
    def __init__(self, path: Path = Path("storage")) -> None:
        if not path.is_dir():
            path.mkdir(exist_ok=True)
        self.path = path

    def enqueue(self, cmd: str) -> None:
        now = datetime.now()
        file = self.path / now.strftime("%Y-%m-%d-%H-%M-%S-%f")
        if file.is_file():
            self.enqueue(cmd)
        with file.open("w") as f:
            f.write(cmd)

    def dequeue(self) -> Optional[BaseQueueModel]:
        files = list(self.path.glob("*-*-*-*-*-*-*"))
        if not files:
            return None

        times = [datetime.strptime(f.name, "%Y-%m-%d-%H-%M-%S-%f") for f in files]
        minn: datetime = times[0]
        minn_idx = 0
        for idx, time in enumerate(times):
            if time < minn:
                minn_idx = idx
        target = files[minn_idx]
        with target.open() as f:
            cmd = f.read()
        target.rename("done/" + target.name)
        return BaseQueueModel(id=target.name, command=cmd, order=0)

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
            with target.open() as f:
                out.append(
                    BaseQueueModel(id=target.name, order=order, command=f.read())
                )
        return out

    def pop(self, id: str) -> None:
        target = self.path / id
        if not target.is_file():
            raise FileNotFoundError
        target.unlink()


class Queues(Enum):
    file = "file"
    redis = "redis"
    db = "db"


QUEUE_CLASSES: Dict[Queues, Type[BaseQueue]] = {Queues.file: FileQueue}
