from __future__ import annotations

from app.storage.database import connect


def test_connect_enables_wal_and_busy_timeout(tmp_path, monkeypatch):
    monkeypatch.setenv("SILVERTECH_DB_PATH", str(tmp_path / "pragma.sqlite3"))
    import importlib
    from app.storage import database
    importlib.reload(database)
    conn = database.connect()
    try:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] >= 3000
    finally:
        conn.close()
