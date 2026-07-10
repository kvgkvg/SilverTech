from __future__ import annotations

import pytest

from app.services.promotion_service import PromotionError, validate_labels


def test_a_complete_submission_validates(make_labels):
    validate_labels(make_labels())


def test_a_missing_logo_bbox_is_rejected(make_labels):
    with pytest.raises(PromotionError, match="logo_bbox"):
        validate_labels(make_labels(template={"logo_bbox": None}))


def test_a_zero_width_logo_is_rejected(make_labels):
    # compute_button_offsets divides by the logo width.
    logo = {"x": 0, "y": 0, "width": 0, "height": 10}
    with pytest.raises(PromotionError, match="logo_bbox"):
        validate_labels(make_labels(template={"logo_bbox": logo}))


def test_a_submission_without_buttons_is_rejected(make_labels):
    with pytest.raises(PromotionError, match="no buttons"):
        validate_labels(make_labels(buttons=[]))


def test_duplicate_button_ids_are_rejected(make_labels):
    button = make_labels()["buttons"][0]
    with pytest.raises(PromotionError, match="duplicate"):
        validate_labels(make_labels(buttons=[button, dict(button)]))


def test_a_button_drawn_without_a_name_is_rejected(make_labels):
    # Matches seed.is_labeled_button: the name is what TTS reads aloud.
    button = dict(make_labels()["buttons"][0], vietnamese_name="  ")
    with pytest.raises(PromotionError, match="name"):
        validate_labels(make_labels(buttons=[button]))


def test_a_degenerate_button_bbox_is_rejected(make_labels):
    button = dict(
        make_labels()["buttons"][0],
        bbox_template_coordinates={"x": 10, "y": 10, "width": 0, "height": 50},
    )
    with pytest.raises(PromotionError, match="bbox"):
        validate_labels(make_labels(buttons=[button]))


def test_an_unknown_button_type_is_rejected(make_labels):
    # buttons.button_type has a CHECK constraint; a bad value fails the insert.
    button = dict(make_labels()["buttons"][0], button_type="slider")
    with pytest.raises(PromotionError, match="button_type"):
        validate_labels(make_labels(buttons=[button]))
