from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DB_PATH = ROOT / "apps" / "api" / "silvertech.sqlite3"
DB_PATH = Path(os.getenv("SILVERTECH_DB_PATH", str(DEFAULT_DB_PATH)))


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS devices (
  id TEXT PRIMARY KEY,
  brand TEXT NOT NULL,
  appliance_type TEXT NOT NULL,
  model_name TEXT,
  display_name TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active', 'archived')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS templates (
  id TEXT PRIMARY KEY,
  device_id TEXT NOT NULL REFERENCES devices(id),
  template_code TEXT NOT NULL,
  template_image_url TEXT NOT NULL,
  logo_bbox TEXT,
  panel_bbox TEXT,
  feature_descriptor_path TEXT,
  version INTEGER NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('official', 'submitted', 'archived')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(device_id, template_code, version)
);

CREATE TABLE IF NOT EXISTS buttons (
  id TEXT PRIMARY KEY,
  template_id TEXT NOT NULL REFERENCES templates(id),
  button_id TEXT NOT NULL,
  label TEXT NOT NULL,
  vietnamese_name TEXT NOT NULL,
  function_description TEXT NOT NULL,
  bbox_template_coordinates TEXT NOT NULL,
  polygon_template_coordinates TEXT,
  button_type TEXT NOT NULL CHECK (button_type IN ('physical', 'touch', 'dial', 'display', 'unknown')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(template_id, button_id)
);

CREATE TABLE IF NOT EXISTS button_offsets (
  template_id TEXT NOT NULL REFERENCES templates(id),
  button_id TEXT NOT NULL,
  dx REAL NOT NULL,
  dy REAL NOT NULL,
  dw REAL NOT NULL,
  dh REAL NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (template_id, button_id)
);

CREATE TABLE IF NOT EXISTS submissions (
  id TEXT PRIMARY KEY,
  submitted_by TEXT,
  brand TEXT NOT NULL,
  appliance_type TEXT NOT NULL,
  image_url TEXT NOT NULL,
  proposed_labels_json TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending', 'accepted', 'rejected')),
  reviewer_note TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS llm_logs (
  id TEXT PRIMARY KEY,
  template_id TEXT NOT NULL REFERENCES templates(id),
  user_query TEXT NOT NULL,
  stt_text TEXT,
  prompt_summary TEXT NOT NULL,
  raw_response TEXT,
  validated_steps_json TEXT,
  validation_status TEXT NOT NULL CHECK (validation_status IN ('accepted', 'regenerated', 'rejected', 'error')),
  latency_ms INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vision_logs (
  id TEXT PRIMARY KEY,
  template_id TEXT REFERENCES templates(id),
  brand_candidate TEXT,
  match_score REAL,
  inlier_count INTEGER,
  inlier_ratio REAL,
  reprojection_error REAL,
  accepted INTEGER NOT NULL CHECK (accepted IN (0, 1)),
  failure_reason TEXT,
  created_at TEXT NOT NULL,
  CHECK ((accepted = 1 AND template_id IS NOT NULL) OR (accepted = 0 AND failure_reason IS NOT NULL))
);
"""


def database_path() -> Path:
    """
    Get the resolved absolute path to the SQLite database file.

    Creates the parent directory if it does not already exist.

    Returns:
        Path: The Path object pointing to the sqlite3 file.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return DB_PATH


def connect() -> sqlite3.Connection:
    """
    Establish a connection to the SQLite database.

    Enables foreign key constraints and configures the connection row factory
    to return sqlite3.Row dict-like rows.

    Returns:
        sqlite3.Connection: The established SQLite connection.
    """
    conn = sqlite3.connect(database_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_session() -> Iterator[sqlite3.Connection]:
    """
    Provide a transactional database session context manager.

    Automatically commits the transaction upon successful completion or
    rolls back in case of exceptions. Closes the connection at the end.

    Yields:
        Iterator[sqlite3.Connection]: The active database connection.
    """
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_database() -> None:
    """
    Create the database schema tables if they do not exist.

    Uses SCHEMA_SQL script containing all table creation scripts.
    """
    with db_session() as conn:
        conn.executescript(SCHEMA_SQL)
