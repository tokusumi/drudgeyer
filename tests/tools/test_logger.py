import tempfile
from pathlib import Path

from drudgeyer.tools.logger import PrintLogger, QueueFileLogger


def test_print(capsys):
    logger = PrintLogger()
    logger.log("test")
    captured = capsys.readouterr()
    assert captured.out == "test"


def test_filelogger():
    logger = QueueFileLogger()
    with tempfile.TemporaryDirectory() as f:
        path = Path(f)
        logger.reset("xxx", "xxx", logdir=path.resolve())
        logger.log("test")

        log = path / "xxx"
        with log.open() as f:
            assert "test\n" == f.readlines()[-1]
