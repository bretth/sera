import pytest
from pathlib import Path, PosixPath


@pytest.fixture
def dotenv_file(monkeypatch):
    tmpenv = Path('/tmp/.env')
    tmpenv.touch()
    monkeypatch.setattr("pathlib.Path.home", lambda: PosixPath('/tmp'))
    yield tmpenv
    tmpenv.unlink()
