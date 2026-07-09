from __future__ import annotations

import pytest

from scripts.label_pipeline.detect import detect_buttons, slug

PANASONIC = {"width": 5712, "height": 4284}


def reply(*items, regions=None):
    body = {"detections": list(items)}
    if regions:
        body["regions"] = regions
    return body


def test_slug_matches_the_label_web_rules():
    # label_web/app.js: trim, lowercase, strip diacritics, non-alphanumerics to _,
    # then trim leading and trailing underscores.
    assert slug("  Micro Power ") == "micro_power"
    assert slug("Time 10 min") == "time_10_min"
    assert slug("Stop/Reset") == "stop_reset"
    assert slug("Vi sóng") == "vi_song"
    assert slug("Quick 30!!") == "quick_30"
    assert slug("---") == ""
    assert slug("") == ""


def test_a_detection_becomes_a_button_with_a_slugged_id():
    body = detect_buttons(
        reply(
            {
                "label_text": "Micro Power",
                "box_2d": [100, 500, 200, 750],
                "confidence": 0.86,
            }
        ),
        **PANASONIC,
    )
    button = body["detections"][0]
    assert button["button_id"] == "micro_power"
    assert button["label_text"] == "Micro Power"
    assert button["confidence"] == 0.86
    assert button["bbox_template_coordinates"] == {
        "x": 2856,
        "y": 428,
        "width": 1428,
        "height": 429,
    }


def test_the_raw_box_2d_is_kept_beside_the_converted_box():
    # When a box is wrong, this distinguishes "the model guessed wrong" from "our
    # conversion is wrong", without spending another API call.
    body = detect_buttons(
        reply({"label_text": "Start", "box_2d": [1, 2, 3, 4], "confidence": 0.9}),
        **PANASONIC,
    )
    assert body["detections"][0]["box_2d"] == [1, 2, 3, 4]


def test_an_icon_only_button_gets_a_null_id_and_is_never_invented():
    # A wrong button_id breaks the validation gate in services/guidance_service.py.
    body = detect_buttons(
        reply({"label_text": "", "box_2d": [1, 2, 3, 4], "confidence": 0.4}),
        **PANASONIC,
    )
    assert body["detections"][0]["button_id"] is None


def test_a_detection_without_a_box_is_dropped_with_a_recorded_reason():
    body = detect_buttons(
        reply(
            {"label_text": "Start", "confidence": 0.9},
            {"label_text": "Stop", "box_2d": [1, 2, 3, 4], "confidence": 0.9},
        ),
        **PANASONIC,
    )
    assert [d["label_text"] for d in body["detections"]] == ["Stop"]
    assert body["dropped"] == [{"label_text": "Start", "reason": "no box_2d"}]


def test_a_malformed_box_is_dropped_rather_than_crashing_the_stage():
    body = detect_buttons(
        reply({"label_text": "Start", "box_2d": [1, 2, 3]}), **PANASONIC
    )
    assert body["detections"] == []
    assert body["dropped"][0]["reason"].startswith("bad box_2d")


def test_a_missing_confidence_defaults_to_zero_not_to_one():
    # Absent evidence is not evidence of correctness; low_confidence should flag it.
    body = detect_buttons(
        reply({"label_text": "Start", "box_2d": [1, 2, 3, 4]}), **PANASONIC
    )
    assert body["detections"][0]["confidence"] == 0.0


def test_logo_and_panel_regions_are_converted_too():
    body = detect_buttons(
        reply(
            regions={
                "logo": [100, 500, 200, 750],
                "panel": [0, 0, 1000, 1000],
            }
        ),
        **PANASONIC,
    )
    assert body["regions"]["logo"] == {
        "x": 2856,
        "y": 428,
        "width": 1428,
        "height": 429,
    }
    assert body["regions"]["panel"] == {
        "x": 0,
        "y": 0,
        "width": 5712,
        "height": 4284,
    }


def test_a_missing_region_is_null_not_absent():
    body = detect_buttons(reply(), **PANASONIC)
    assert body["regions"] == {"logo": None, "panel": None}


def test_the_image_dimensions_are_recorded():
    body = detect_buttons(reply(), **PANASONIC)
    assert body["image"]["width"] == 5712
    assert body["image"]["height"] == 4284


def test_a_reply_with_no_detections_key_raises():
    with pytest.raises(ValueError, match="detections"):
        detect_buttons({"buttons": []}, **PANASONIC)
