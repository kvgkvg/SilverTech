"""Alembic placeholder.

The MVP uses a stdlib SQLite schema runner so the project can run in this
environment without SQLAlchemy installed. The schema is kept PostgreSQL-friendly
and can be migrated to Alembic/SQLAlchemy when production deployment starts.
"""

from app.storage.database import initialize_database


def run_migrations() -> None:
    initialize_database()


if __name__ == "__main__":
    run_migrations()
