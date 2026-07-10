from __future__ import annotations

from pathlib import Path

import pytest

from app.services.promotion_service import PromotionError, promote_submission

SUBMISSION_ID = "ab12cd34-0000-0000-0000-000000000000"


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, promotion_dirs):
    monkeypatch.setenv("SILVERTECH_DB_PATH", str(tmp_path / "promo.sqlite3"))
    from app.storage.database import connect, initialize_database

    initialize_database()
    connection = connect()
    yield connection
    connection.close()


def test_it_returns_a_template_id_derived_from_the_submission(conn, make_labels):
    assert promote_submission(conn, SUBMISSION_ID, make_labels()) == "template_ab12cd34"


def test_the_client_supplied_template_id_is_ignored(conn, make_labels):
    promote_submission(conn, SUBMISSION_ID, make_labels())
    ids = [r["id"] for r in conn.execute("SELECT id FROM templates")]
    assert ids == ["template_ab12cd34"]


def test_the_device_is_active_and_the_template_is_official(conn, make_labels):
    # list_candidates filters on exactly these two columns; get either wrong and
    # the promoted template is invisible to the camera.
    promote_submission(conn, SUBMISSION_ID, make_labels())
    assert conn.execute("SELECT status FROM devices").fetchone()["status"] == "active"
    assert conn.execute("SELECT status FROM templates").fetchone()["status"] == "official"


def test_it_writes_every_button(conn, make_labels):
    promote_submission(conn, SUBMISSION_ID, make_labels())
    rows = conn.execute("SELECT id, button_id FROM buttons ORDER BY button_id").fetchall()
    assert [r["button_id"] for r in rows] == ["1", "2"]
    assert [r["id"] for r in rows] == ["btn_ab12cd34_1", "btn_ab12cd34_2"]


def test_it_writes_button_offsets(conn, make_labels):
    # The whole feature turns on this table. run_logo_anchor raises 409
    # "no button_offsets" without it.
    from scripts.logo_anchor import compute_button_offsets

    labels = make_labels()
    promote_submission(conn, SUBMISSION_ID, labels)
    expected = compute_button_offsets(
        labels["template"]["logo_bbox"],
        {b["button_id"]: b["bbox_template_coordinates"] for b in labels["buttons"]},
    )
    rows = conn.execute("SELECT button_id, dx, dy, dw, dh FROM button_offsets").fetchall()
    actual = {r["button_id"]: {"dx": r["dx"], "dy": r["dy"], "dw": r["dw"], "dh": r["dh"]} for r in rows}
    assert actual == expected


def test_the_template_points_at_the_copied_image(conn, make_labels):
    promote_submission(conn, SUBMISSION_ID, make_labels())
    row = conn.execute("SELECT template_image_url, template_code FROM templates").fetchone()
    assert row["template_image_url"] == "data/templates/template_ab12cd34.png"
    assert row["template_code"] == "panasonic_microwave_nn_gt35hm_v1"


def test_invalid_labels_write_nothing(conn, make_labels):
    with pytest.raises(PromotionError):
        promote_submission(conn, SUBMISSION_ID, make_labels(template={"logo_bbox": None}))
    assert conn.execute("SELECT count(*) AS n FROM devices").fetchone()["n"] == 0


def test_a_missing_photo_writes_nothing(conn, make_labels):
    labels = make_labels(template={"template_image_url": "data/submissions/gone.png"})
    with pytest.raises(PromotionError):
        promote_submission(conn, SUBMISSION_ID, labels)
    assert conn.execute("SELECT count(*) AS n FROM templates").fetchone()["n"] == 0
