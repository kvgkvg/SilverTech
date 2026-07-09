"""Compute logo-relative button offsets for every template and store them in SQLite.

Offsets are normalized by logo width (see scripts.logo_anchor.compute_button_offsets)
so the runtime can place buttons from a detected logo pose alone.

Usage:
    PYTHONPATH=apps/vision-tools python apps/vision-tools/scripts/compute_logo_offsets.py \
        [--db apps/api/silvertech.sqlite3] [--template-id ID]
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from scripts.logo_anchor import compute_button_offsets

ROOT = Path(__file__).resolve().parents[3]
# Match app.storage.database, so seeding and offsets always land in the same file.
DEFAULT_DB = Path(os.getenv("SILVERTECH_DB_PATH", str(ROOT / "apps" / "api" / "silvertech.sqlite3")))

OFFSETS_TABLE_SQL = """
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
"""


def compute_for_template(conn: sqlite3.Connection, template_id: str) -> int:
    row = conn.execute(
        "SELECT id, logo_bbox FROM templates WHERE id = :id", {"id": template_id}
    ).fetchone()
    if row is None:
        raise SystemExit(f"template not found: {template_id}")
    if not row["logo_bbox"]:
        raise SystemExit(f"template {template_id} has no logo_bbox; label the logo first")
    logo_bbox = json.loads(row["logo_bbox"])
    buttons = {
        b["button_id"]: json.loads(b["bbox_template_coordinates"])
        for b in conn.execute(
            "SELECT button_id, bbox_template_coordinates FROM buttons WHERE template_id = :id",
            {"id": template_id},
        ).fetchall()
    }
    offsets = compute_button_offsets(logo_bbox, buttons)
    now = datetime.now(timezone.utc).isoformat()
    for button_id, off in offsets.items():
        conn.execute(
            """
            INSERT OR REPLACE INTO button_offsets
                (template_id, button_id, dx, dy, dw, dh, updated_at)
            VALUES (:template_id, :button_id, :dx, :dy, :dw, :dh, :updated_at)
            """,
            {"template_id": template_id, "button_id": button_id, "updated_at": now, **off},
        )
    return len(offsets)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--template-id", default=None, help="single template; default: all")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    conn.executescript(OFFSETS_TABLE_SQL)
    if args.template_id:
        template_ids = [args.template_id]
    else:
        template_ids = [r["id"] for r in conn.execute("SELECT id FROM templates").fetchall()]
    total = 0
    for template_id in template_ids:
        count = compute_for_template(conn, template_id)
        print(f"{template_id}: {count} offsets")
        total += count
    conn.commit()
    conn.close()
    print(f"done: {total} offsets across {len(template_ids)} templates")


if __name__ == "__main__":
    main()
