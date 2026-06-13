from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SILVERTECH_DB_PATH", str(tmp_path / "contract.sqlite3"))
    # Force the deterministic mock LLM so contract tests don't depend on a local
    # .env that may set SILVERTECH_LLM_PROVIDER=openrouter (whose live call fails
    # offline/in CI and would surface as a 502).
    monkeypatch.setenv("SILVERTECH_LLM_PROVIDER", "mock")
    from app.storage.seed import seed_database

    seed_database()
    from app.main import app

    return TestClient(app)
