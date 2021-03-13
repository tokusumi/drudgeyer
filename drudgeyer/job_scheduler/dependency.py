from abc import ABC, abstractmethod
from pathlib import Path
from shutil import copytree, rmtree
from typing import Optional


class BaseDep(ABC):
    @property
    @abstractmethod
    def path(self) -> Path:
        ...  # pragma: no cover

    @abstractmethod
    async def dump(self, id: str) -> None:
        ...  # pragma: no cover

    @abstractmethod
    def workdir(self, id: str) -> Path:
        ...  # pragma: no cover

    @abstractmethod
    async def clear(self, id: str) -> None:
        ...  # pragma: no cover


class CopyDep(BaseDep):
    def __init__(
        self,
        target: Optional[Path] = None,
        path: Path = Path("dep"),
    ) -> None:
        self._path = path
        if not self._path.is_dir():
            self._path.mkdir(parents=True, exist_ok=True)

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
            raise FileExistsError()

        if self._target:
            save_to.mkdir(parents=True, exist_ok=True)
            save_to = save_to / self._target.name
            copytree(self._target, save_to, symlinks=False, ignore=None)

    def workdir(self, id: str) -> Path:
        if not id:
            raise ValueError()
        return self.path / id

    async def clear(self, id: str) -> None:
        if id:
            rmtree((self.path / id), ignore_errors=True)
