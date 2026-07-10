from __future__ import annotations

import argparse
import json

from scripts.label_pipeline.pipeline import _merge, build_draft, run

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


class _FakeGeminiClient:
    """Stands in for GeminiClient: canned detect/describe replies, no network."""

    model = "fake-model-1"

    def prompt_version(self, prompt: str) -> str:
        return "sha256:fake"

    def generate_json(self, prompt, *, image=None, mime_type="image/png"):
        if image is not None:
            # detect.py's call: image is present.
            return {
                "detections": [
                    {"label_text": "Start", "box_2d": [100, 100, 300, 400], "confidence": 0.9},
                ],
                "regions": {
                    "logo": [0, 0, 50, 50],
                    "panel": [0, 0, 1000, 1000],
                },
            }
        # describe.py's call: no image.
        return {
            "buttons": [
                {
                    "button_id": "start",
                    "vietnamese_name": "Bắt đầu",
                    "function_description": "bắt đầu nấu",
                    "manual_evidence": {"page": 1, "quote": "Nhấn Start để bắt đầu."},
                }
            ]
        }


def test_run_writes_a_draft_and_qc_report_with_intermediates_under_pipeline(
    tmp_path, monkeypatch
):
    # This is the missing coverage that let the seed.py collision (Finding 1) ship
    # unseen: run() and main() had zero tests, so nothing exercised the file names
    # run() actually writes.
    from PIL import Image

    import scripts.label_pipeline.extract as extract_module
    from scripts.label_pipeline.extract import PageSource

    image_path = tmp_path / "panel.png"
    Image.new("RGB", (1200, 900), color="white").save(image_path)

    manual_page = PageSource(
        1, "Nhấn Start để bắt đầu quá trình nấu ăn một cách nhanh chóng.", None
    )
    monkeypatch.setattr(extract_module, "read_pdf", lambda _path: [manual_page])

    out_path = tmp_path / "acme_toaster_t100_v1.draft.json"
    args = argparse.Namespace(
        manual=str(tmp_path / "manual.pdf"),
        image=str(image_path),
        out=str(out_path),
        brand="Acme",
        model_name="T-100",
        appliance_type="toaster",
        display_name=None,
        template_code=None,
        model="fake-model-1",
        confidence_threshold=0.5,
    )

    run(args, client=_FakeGeminiClient())

    report_path = out_path.with_name(out_path.name.replace(".draft.json", ".qc_report.json"))
    assert out_path.exists()
    assert report_path.exists()

    draft = json.loads(out_path.read_text(encoding="utf-8"))
    assert set(draft) == {"device", "template", "buttons"}

    # seed.py (Finding 1's fix) deliberately skips every "*.draft.json" file when it
    # globs data/templates/labels/, so a template with status "draft" never reaches
    # the `templates.status` CHECK constraint -- it is simply never seeded until a
    # human reviews and renames the file. Asserting "draft" here pins that contract.
    assert draft["template"]["status"] == "draft"

    work_dir = out_path.parent / ".pipeline" / image_path.stem
    assert (work_dir / "manual_text.json").exists()
    assert (work_dir / "detections.json").exists()
    assert (work_dir / "described.json").exists()
