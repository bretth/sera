import pytest
from pathlib import Path, PosixPath


@pytest.fixture
def dotenv_file(monkeypatch):
    tmpenv = Path('/tmp/.env')
    tmpenv.touch()
    monkeypatch.setattr("pathlib.Path.home", lambda: PosixPath('/tmp'))
    yield tmpenv
    tmpenv.unlink()


@pytest.fixture
def allowed_clients_file(monkeypatch):
    tmpclients = Path('/tmp/.allowed_sera_clients')
    tmpclients.touch()
    with open(str(tmpclients), 'w') as f:
        f.write('123\n')
        f.write('456\n')
    yield tmpclients
    tmpclients.unlink

