from __future__ import annotations

from pathlib import Path

from app.storage.seed import is_reviewed_label_file


def test_a_draft_json_is_ignored():
    # label_pipeline/pipeline.py writes this with template status "draft", which
    # the templates.status CHECK constraint rejects.
    path = Path("data/templates/labels/panasonic_microwave_nn_gt35hm_v1.draft.json")
    assert not is_reviewed_label_file(path)


def test_a_qc_report_json_is_ignored():
    # No "device" key at all, so seed_database's label["device"] would KeyError.
    path = Path("data/templates/labels/panasonic_microwave_nn_gt35hm_v1.qc_report.json")
    assert not is_reviewed_label_file(path)


def test_an_ordinary_json_is_selected():
    path = Path("data/templates/labels/panasonic_microwave_nn_gt35hm_v1.json")
    assert is_reviewed_label_file(path)


def test_a_reviewed_file_renamed_to_drop_draft_is_still_selected():
    # A human reviews the draft in label_web/ and renames it to drop ".draft".
    # That renamed file must be picked up even though its stem is the same.
    path = Path("data/templates/labels/foo.json")
    assert is_reviewed_label_file(path)
