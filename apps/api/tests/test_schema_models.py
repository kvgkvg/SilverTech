from __future__ import annotations

from app.services.template_repository import get_template, list_candidates, valid_button_ids


def test_seeded_templates_are_official_and_have_buttons(client):
    candidates = list_candidates("Toshiba", "washing_machine")
    assert candidates
    assert all(candidate["status"] == "official" for candidate in candidates)
    template = get_template(candidates[0]["id"])
    assert template is not None
    assert {"start_pause", "quick_wash", "dry_mode"}.issubset(valid_button_ids(template["id"]))
