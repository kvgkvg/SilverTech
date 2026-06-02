from __future__ import annotations

from app.storage.database import db_session


def test_sqlite_schema_contains_core_tables(client):
    with db_session() as conn:
        tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
    assert {"devices", "templates", "buttons", "submissions", "llm_logs", "vision_logs"}.issubset(tables)
