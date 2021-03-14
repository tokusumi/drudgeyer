import tempfile
from pathlib import Path

import pytest

from drudgeyer.job_scheduler.dependency import CopyDep


@pytest.mark.asyncio
async def test_copydep():
    with tempfile.TemporaryDirectory() as f:
        target = Path(f) / "src"
        target.mkdir()
        (target / "a").mkdir()
        (target / "a" / "a.txt").touch()
        (target / "b").mkdir()
        (target / "b" / "b.txt").touch()

        path = Path(f) / "dest"

        dep = CopyDep(target, path)

        # save dependency
        await dep.dump("xxx")

        with pytest.raises(FileExistsError):
            # avoid override
            await dep.dump("xxx")

        assert (path / "xxx" / "src").is_dir()
        assert (path / "xxx" / "src" / "a").is_dir()
        assert (path / "xxx" / "src" / "a" / "a.txt").is_file()
        assert (path / "xxx" / "src" / "b").is_dir()
        assert (path / "xxx" / "src" / "b" / "b.txt").is_file()

        # get working directory to execute command
        workdir = dep.workdir("xxx")
        assert workdir == (path / "xxx" / "src")

        # delete dependency
        await dep.clear("xxx")
        assert not (path / "xxx").is_dir()


@pytest.mark.asyncio
async def test_copydep_failed():
    with tempfile.TemporaryDirectory() as f:
        path = Path(f) / "dest"

        # call mode
        dep = CopyDep(None, path)

        # no error and no save
        await dep.dump("xxx")
        await dep.dump("")

        # get working directory to execute command
        with pytest.raises(ValueError):
            dep.workdir("")

        # no error and no deletion
        await dep.clear("")
