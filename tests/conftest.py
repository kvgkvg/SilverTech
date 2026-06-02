from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SILVERTECH_DB_PATH", str(tmp_path / "contract.sqlite3"))
    from app.storage.seed import seed_database

    seed_database()
    from app.main import app

    return TestClient(app)
