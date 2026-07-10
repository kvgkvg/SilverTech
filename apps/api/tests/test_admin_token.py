from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SILVERTECH_DB_PATH", str(tmp_path / "auth.sqlite3"))
    from app.storage.seed import seed_database

    seed_database()
    from app.main import app

    return TestClient(app)


def test_without_the_header_the_request_is_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("SILVERTECH_ADMIN_TOKEN", "s3cret")
    response = _client(tmp_path, monkeypatch).post(
        "/api/admin/submissions/whatever/review", json={"decision": "reject"}
    )
    assert response.status_code == 401


def test_a_wrong_token_is_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("SILVERTECH_ADMIN_TOKEN", "s3cret")
    response = _client(tmp_path, monkeypatch).post(
        "/api/admin/submissions/whatever/review",
        json={"decision": "reject"},
        headers={"X-Admin-Token": "guess"},
    )
    assert response.status_code == 401


def test_an_unset_token_closes_the_router(tmp_path, monkeypatch):
    # Default closed. Forgetting to configure the server must not be the thing
    # that opens the door.
    monkeypatch.delenv("SILVERTECH_ADMIN_TOKEN", raising=False)
    response = _client(tmp_path, monkeypatch).post(
        "/api/admin/submissions/whatever/review",
        json={"decision": "reject"},
        headers={"X-Admin-Token": "anything"},
    )
    assert response.status_code == 503


def test_the_right_token_reaches_the_handler(tmp_path, monkeypatch):
    monkeypatch.setenv("SILVERTECH_ADMIN_TOKEN", "s3cret")
    response = _client(tmp_path, monkeypatch).post(
        "/api/admin/submissions/whatever/review",
        json={"decision": "reject"},
        headers={"X-Admin-Token": "s3cret"},
    )
    assert response.status_code == 404  # past the guard, submission not found
