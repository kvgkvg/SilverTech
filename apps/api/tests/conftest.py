from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SILVERTECH_DB_PATH", str(tmp_path / "test.sqlite3"))
    monkeypatch.setenv("SILVERTECH_LLM_PROVIDER", "mock")
    from app.storage.seed import seed_database

    seed_database()
    from app.main import app

    return TestClient(app)


@pytest.fixture()
def make_labels():
    """Reviewed labels in the shape POST /api/submissions stores them.

    The `status` values and the template `id` are what the mobile wizard
    actually sends. Promotion must discard all three.
    """

    def _make(device=None, template=None, buttons=None):
        base_device = {
            "brand": "Panasonic",
            "appliance_type": "microwave",
            "model_name": "NN-GT35HM",
            "display_name": "Lo vi song Panasonic",
            "status": "submitted",
        }
        base_template = {
            "id": "template_from_the_client",
            "template_code": "panasonic_microwave_nn_gt35hm_v1",
            "template_image_url": "data/submissions/abc.png",
            "logo_bbox": {"x": 0, "y": 0, "width": 100, "height": 40},
            "panel_bbox": {"x": 0, "y": 0, "width": 800, "height": 600},
            "status": "submitted",
        }
        base_buttons = [
            {
                "button_id": "1",
                "label": "Start",
                "vietnamese_name": "khoi dong",
                "function_description": "bat dau",
                "bbox_template_coordinates": {"x": 200, "y": 100, "width": 50, "height": 50},
                "button_type": "physical",
            },
            {
                "button_id": "2",
                "label": "Stop",
                "vietnamese_name": "dung",
                "function_description": "dung lai",
                "bbox_template_coordinates": {"x": 300, "y": 100, "width": 50, "height": 50},
                "button_type": "touch",
            },
        ]
        return {
            "device": {**base_device, **(device or {})},
            "template": {**base_template, **(template or {})},
            "buttons": base_buttons if buttons is None else buttons,
        }

    return _make


@pytest.fixture()
def promotion_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point promotion_service at throwaway data/ directories.

    Yields (submissions_dir, templates_dir) with one fake photo already in the
    submissions dir at the path make_labels' template_image_url names.
    """
    from app.services import promotion_service

    submissions = tmp_path / "data" / "submissions"
    templates = tmp_path / "data" / "templates"
    submissions.mkdir(parents=True)
    templates.mkdir(parents=True)
    (submissions / "abc.png").write_bytes(b"fake-png")
    monkeypatch.setattr(promotion_service, "ROOT", tmp_path)
    monkeypatch.setattr(promotion_service, "SUBMISSIONS_DIR", submissions)
    monkeypatch.setattr(promotion_service, "TEMPLATES_DIR", templates)
    return submissions, templates
