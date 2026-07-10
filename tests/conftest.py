from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SILVERTECH_DB_PATH", str(tmp_path / "contract.sqlite3"))
    # Without this, env_loader hands the real provider from .env to the guidance
    # test, and running the contract suite bills a live OpenRouter key.
    monkeypatch.setenv("SILVERTECH_LLM_PROVIDER", "mock")
    from app.storage.seed import seed_database

    seed_database()
    from app.main import app

    return TestClient(app)
