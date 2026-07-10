from __future__ import annotations

import pytest

from app.services.promotion_service import PromotionError, copy_submission_image


def test_it_copies_the_photo_and_returns_the_new_url(promotion_dirs):
    _, templates = promotion_dirs

    url = copy_submission_image("data/submissions/abc.png", "template_ab12cd34")

    assert url == "data/templates/template_ab12cd34.png"
    assert (templates / "template_ab12cd34.png").read_bytes() == b"fake-png"


def test_the_original_survives(promotion_dirs):
    submissions, _ = promotion_dirs
    copy_submission_image("data/submissions/abc.png", "template_ab12cd34")
    assert (submissions / "abc.png").is_file()


def test_a_path_outside_the_submissions_directory_is_rejected(promotion_dirs):
    # image_url arrives from the client in SubmissionCreate.
    with pytest.raises(PromotionError, match="data/submissions"):
        copy_submission_image("data/templates/panasonic.png", "template_ab12cd34")


def test_a_traversing_image_url_is_rejected(promotion_dirs):
    with pytest.raises(PromotionError, match="data/submissions"):
        copy_submission_image("data/submissions/../../etc/passwd", "template_ab12cd34")


def test_a_missing_file_is_rejected(promotion_dirs):
    with pytest.raises(PromotionError, match="missing"):
        copy_submission_image("data/submissions/gone.png", "template_ab12cd34")


def test_an_unsupported_suffix_is_rejected(promotion_dirs):
    submissions, _ = promotion_dirs
    (submissions / "abc.svg").write_bytes(b"<svg/>")
    with pytest.raises(PromotionError, match="image type"):
        copy_submission_image("data/submissions/abc.svg", "template_ab12cd34")


def test_the_destination_name_comes_only_from_the_template_id(promotion_dirs):
    submissions, templates = promotion_dirs
    (submissions / "abc.jpeg").write_bytes(b"x")
    url = copy_submission_image("data/submissions/abc.jpeg", "template_ab12cd34")
    assert url == "data/templates/template_ab12cd34.jpeg"
    assert [p.name for p in templates.iterdir()] == ["template_ab12cd34.jpeg"]
