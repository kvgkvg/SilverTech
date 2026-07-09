from __future__ import annotations

import json

from app.storage.database import ROOT
from app.storage.seed import is_labeled_button


def test_a_named_button_is_kept():
    button = {"button_id": "start", "vietnamese_name": "khởi động"}
    assert is_labeled_button(button)


def test_a_box_drawn_without_a_name_is_skipped():
    button = {"button_id": "", "vietnamese_name": ""}
    assert not is_labeled_button(button)


def test_whitespace_only_names_count_as_unlabeled():
    button = {"button_id": "  ", "vietnamese_name": "khởi động"}
    assert not is_labeled_button(button)


def test_a_button_id_without_a_vietnamese_name_is_skipped():
    # The name is what TTS reads aloud, so a button without one is unusable.
    button = {"button_id": "start", "vietnamese_name": ""}
    assert not is_labeled_button(button)


def test_the_shipped_microwave_labels_carry_exactly_one_unlabeled_box():
    path = ROOT / "data" / "templates" / "labels" / "panasonic_microwave_nn_gt35hm_v1.json"
    buttons = json.loads(path.read_text(encoding="utf-8"))["buttons"]
    skipped = [b for b in buttons if not is_labeled_button(b)]
    assert len(skipped) == 1
    assert len(buttons) - len(skipped) == 15
