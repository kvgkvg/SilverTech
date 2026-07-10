from __future__ import annotations

from pathlib import Path

import pytest

from app.services.promotion_service import PromotionError
from app.services.review_service import AlreadyReviewedError, review_submission
from app.services.submission_service import create_submission


@pytest.fixture()
def submission_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, promotion_dirs, make_labels):
    monkeypatch.setenv("SILVERTECH_DB_PATH", str(tmp_path / "review.sqlite3"))
    from app.storage.database import initialize_database

    initialize_database()
    return create_submission(
        {
            "submitted_by": None,
            "brand": "Panasonic",
            "appliance_type": "microwave",
            "image_url": "data/submissions/abc.png",
            "proposed_labels_json": make_labels(),
        }
    )


def _count(table: str) -> int:
    from app.storage.database import db_session

    with db_session() as conn:
        return conn.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"]


def test_accept_promotes_and_returns_the_template_id(submission_id):
    result = review_submission(submission_id, "accept", None)
    assert result["status"] == "accepted"
    assert result["template_id"].startswith("template_")
    assert _count("templates") == 1


def test_reject_creates_no_template(submission_id):
    result = review_submission(submission_id, "reject", "anh mo")
    assert result == {"submission_id": submission_id, "status": "rejected", "template_id": None}
    assert _count("templates") == 0


def test_edit_promotes_the_edited_labels(submission_id, make_labels):
    labels = make_labels()
    labels["buttons"][0]["vietnamese_name"] = "bat dau ngay"
    review_submission(submission_id, "edit", None, edited_template=labels)

    from app.storage.database import db_session

    with db_session() as conn:
        name = conn.execute(
            "SELECT vietnamese_name FROM buttons WHERE button_id = '1'"
        ).fetchone()["vietnamese_name"]
    assert name == "bat dau ngay"


def test_edit_without_edited_template_is_refused(submission_id):
    with pytest.raises(PromotionError, match="edited_template"):
        review_submission(submission_id, "edit", None)
    assert _count("templates") == 0


def test_reviewing_twice_is_refused_and_changes_nothing(submission_id):
    review_submission(submission_id, "accept", None)
    with pytest.raises(AlreadyReviewedError):
        review_submission(submission_id, "accept", None)
    assert _count("templates") == 1
    assert _count("devices") == 1


def test_an_unknown_submission_raises_key_error(submission_id):
    with pytest.raises(KeyError):
        review_submission("no-such-id", "accept", None)


def test_a_bad_decision_raises_value_error(submission_id):
    with pytest.raises(ValueError):
        review_submission(submission_id, "maybe", None)


def test_a_failed_promotion_leaves_the_submission_pending(submission_id):
    # Rollback must cover the status update too, or a retry is impossible.
    from app.storage.database import db_session

    with db_session() as conn:
        conn.execute("UPDATE submissions SET proposed_labels_json = '{}' WHERE id = :id",
                     {"id": submission_id})
    with pytest.raises(PromotionError):
        review_submission(submission_id, "accept", None)
    with db_session() as conn:
        status = conn.execute("SELECT status FROM submissions WHERE id = :id",
                              {"id": submission_id}).fetchone()["status"]
    assert status == "pending"
