from __future__ import annotations

import json

from scripts.label_pipeline.pipeline import _merge, build_draft

DEVICE = {
    "id": "device_panasonic_microwave_nn_gt35hm",
    "brand": "Panasonic",
    "appliance_type": "microwave",
    "model_name": "NN-GT35HM",
    "display_name": "Lò vi sóng Panasonic NN-GT35HM",
    "status": "active",
}
TEMPLATE = {
    "id": "template_panasonic_microwave_nn_gt35hm_v1",
    "device_id": DEVICE["id"],
    "template_code": "panasonic_microwave_nn_gt35hm_v1",
    "template_image_url": "data/templates/panasonic_microwave_nn_gt35hm.png",
    "version": 1,
    "status": "draft",
}
DETECTIONS = {
    "image": {"width": 5712, "height": 4284},
    "regions": {"logo": {"x": 1, "y": 2, "width": 3, "height": 4}, "panel": None},
    "detections": [
        {
            "button_id": "start",
            "label_text": "Start",
            "bbox_template_coordinates": {"x": 10, "y": 10, "width": 50, "height": 50},
            "confidence": 0.9,
        }
    ],
}
QC_BUTTONS = [
    {
        "button_id": "start",
        "label_text": "Start",
        "vietnamese_name": "Bắt đầu",
        "function_description": "bắt đầu nấu",
        "manual_evidence": {"page": 1, "quote": "Nhấn Start."},
        "bbox_template_coordinates": {"x": 10, "y": 10, "width": 50, "height": 50},
        "confidence": 0.9,
        "qc": {"status": "pass", "issues": [], "confidence": 0.9},
    }
]


def test_the_draft_has_the_three_top_level_blocks_seed_expects():
    draft = build_draft(
        detections=DETECTIONS, qc_buttons=QC_BUTTONS, device=DEVICE, template=TEMPLATE,
    )
    assert set(draft) == {"device", "template", "buttons"}


def test_each_button_carries_the_columns_seed_inserts():
    draft = build_draft(detections=DETECTIONS, qc_buttons=QC_BUTTONS,
                        device=DEVICE, template=TEMPLATE)
    button = draft["buttons"][0]
    for key in ("id", "template_id", "button_id", "label", "vietnamese_name",
                "function_description", "bbox_template_coordinates",
                "polygon_template_coordinates", "button_type"):
        assert key in button, key


def test_the_button_row_id_follows_label_webs_naming():
    draft = build_draft(detections=DETECTIONS, qc_buttons=QC_BUTTONS,
                        device=DEVICE, template=TEMPLATE)
    assert draft["buttons"][0]["id"] == "btn_panasonic_microwave_nn_gt35hm_v1_start"
    assert draft["buttons"][0]["template_id"] == TEMPLATE["id"]


def test_qc_rides_inside_the_button_so_label_web_reads_one_file():
    draft = build_draft(detections=DETECTIONS, qc_buttons=QC_BUTTONS,
                        device=DEVICE, template=TEMPLATE)
    assert draft["buttons"][0]["qc"]["status"] == "pass"


def test_the_detected_regions_populate_logo_and_panel_bbox():
    draft = build_draft(detections=DETECTIONS, qc_buttons=QC_BUTTONS,
                        device=DEVICE, template=TEMPLATE)
    assert draft["template"]["logo_bbox"] == {"x": 1, "y": 2, "width": 3, "height": 4}
    assert draft["template"]["panel_bbox"] is None


def test_a_null_id_button_gets_a_row_id_from_its_index_not_from_none():
    qc_buttons = [{**QC_BUTTONS[0], "button_id": None, "label_text": ""}]
    draft = build_draft(detections=DETECTIONS, qc_buttons=qc_buttons,
                        device=DEVICE, template=TEMPLATE)
    assert draft["buttons"][0]["id"].endswith("_unnamed_0")
    assert draft["buttons"][0]["button_id"] == ""


def test_the_draft_is_json_serialisable_without_ascii_escaping():
    draft = build_draft(detections=DETECTIONS, qc_buttons=QC_BUTTONS,
                        device=DEVICE, template=TEMPLATE)
    text = json.dumps(draft, ensure_ascii=False)
    assert "Bắt đầu" in text


def test_the_draft_button_type_defaults_to_touch():
    draft = build_draft(detections=DETECTIONS, qc_buttons=QC_BUTTONS,
                        device=DEVICE, template=TEMPLATE)
    assert draft["buttons"][0]["button_type"] == "touch"


def test_a_template_missing_feature_descriptor_path_gets_none_so_seed_can_bind_it():
    assert "feature_descriptor_path" not in TEMPLATE
    draft = build_draft(detections=DETECTIONS, qc_buttons=QC_BUTTONS,
                        device=DEVICE, template=TEMPLATE)
    assert draft["template"]["feature_descriptor_path"] is None


def test_an_explicit_feature_descriptor_path_is_not_overridden():
    template = {**TEMPLATE, "feature_descriptor_path": "data/descriptors/foo.npz"}
    draft = build_draft(detections=DETECTIONS, qc_buttons=QC_BUTTONS,
                        device=DEVICE, template=template)
    assert draft["template"]["feature_descriptor_path"] == "data/descriptors/foo.npz"


def test_a_null_id_described_button_is_never_attributed_to_a_null_id_detection():
    detections = {
        **DETECTIONS,
        "detections": [
            {
                "button_id": None,
                "label_text": "",
                "bbox_template_coordinates": {"x": 1, "y": 1, "width": 5, "height": 5},
                "confidence": 0.8,
            }
        ],
    }
    described = {
        "buttons": [
            {
                "button_id": None,
                "vietnamese_name": "SAI: không nên gán cho nút không tên",
                "function_description": "SAI",
            }
        ]
    }
    merged = _merge(detections, described)
    assert merged[0]["vietnamese_name"] == ""
    assert merged[0]["function_description"] == ""
