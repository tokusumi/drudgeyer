from abc import ABC, abstractmethod
from pathlib import Path
from shutil import copytree
from typing import Optional


class BaseDep(ABC):
    @property
    @abstractmethod
    def path(self) -> Path:
        ...

    @abstractmethod
    async def dump(self, id: str) -> None:
        ...

    @abstractmethod
    def workdir(self, id: str) -> Path:
        ...

    @abstractmethod
    async def clear(self, id: str) -> None:
        ...


class CopyDep(BaseDep):
    def __init__(
        self,
        target: Optional[Path] = None,
        path: Path = Path("dep"),
    ) -> None:
        self._path = path

        # for enqueue
        self._target = target

    @property
    def path(self) -> Path:
        return self._path

    async def dump(self, id: str) -> None:
        if not id:
            return

        save_to = self.path / id
        if save_to.is_dir():
            raise FileExistsError

        if self._target:
            copytree(self._target, save_to, symlinks=False, ignore=None)

    def workdir(self, id: str) -> Path:
        return self.path / id

    async def clear(self, id: str) -> None:
        if id:
            (self.path / id).rmdir()
