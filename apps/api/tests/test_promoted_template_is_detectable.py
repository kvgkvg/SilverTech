from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

cv2 = pytest.importorskip("cv2")

REAL_ROOT = Path(__file__).resolve().parents[3]
PANEL = REAL_ROOT / "data" / "templates" / "panasonic_microwave_nn_gt35hm.png"
LABELS = REAL_ROOT / "data" / "templates" / "labels" / "panasonic_microwave_nn_gt35hm_v1.json"


@pytest.fixture()
def promoted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SILVERTECH_DB_PATH", str(tmp_path / "detect.sqlite3"))
    from app.services import promotion_service
    from app.services.review_service import review_submission
    from app.services.submission_service import create_submission
    from app.storage.database import initialize_database

    initialize_database()  # empty DB: no seeded template shares this photo

    submissions = tmp_path / "data" / "submissions"
    templates = tmp_path / "data" / "templates"
    submissions.mkdir(parents=True)
    templates.mkdir(parents=True)
    shutil.copyfile(PANEL, submissions / "panel.png")
    monkeypatch.setattr(promotion_service, "ROOT", tmp_path)
    monkeypatch.setattr(promotion_service, "SUBMISSIONS_DIR", submissions)
    monkeypatch.setattr(promotion_service, "TEMPLATES_DIR", templates)

    # logo_anchor_service resolves template_image_url against its own ROOT.
    from app.services import logo_anchor_service

    monkeypatch.setattr(logo_anchor_service, "ROOT", tmp_path)

    reviewed = json.loads(LABELS.read_text(encoding="utf-8"))
    labels = {
        "device": reviewed["device"],
        "template": {
            "template_code": "panasonic_microwave_nn_gt35hm_v1",
            "template_image_url": "data/submissions/panel.png",
            "logo_bbox": reviewed["template"]["logo_bbox"],
            "panel_bbox": reviewed["template"]["panel_bbox"],
        },
        "buttons": reviewed["buttons"][:3],
    }
    submission_id = create_submission(
        {
            "submitted_by": None,
            "brand": "Panasonic",
            "appliance_type": "microwave",
            "image_url": "data/submissions/panel.png",
            "proposed_labels_json": labels,
        }
    )
    result = review_submission(submission_id, "accept", None)
    return result["template_id"]


def test_the_promoted_template_is_a_detection_candidate(promoted):
    # Wrong device/template status and list_candidates filters it straight out.
    from app.services.template_repository import list_candidates

    assert promoted in {c["id"] for c in list_candidates(None, None)}


def test_run_logo_anchor_matches_the_promoted_template(promoted):
    # Without button_offsets this raises 409 "no button_offsets; run
    # compute_logo_offsets.py first" -- the omission that made the whole
    # submission flow inert.
    from app.services.logo_anchor_service import run_logo_anchor

    result = run_logo_anchor(promoted, PANEL.read_bytes())

    assert result["template_id"] == promoted
    assert result["accepted"] is True
    assert set(result["projected_buttons"]) == {"micro_power", "time_10_min", "grill"}
