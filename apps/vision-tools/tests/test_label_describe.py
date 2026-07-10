from __future__ import annotations

import json

import pytest

from scripts.label_pipeline.describe import describe_buttons, write_descriptions


def test_a_described_button_carries_its_evidence():
    reply = {
        "buttons": [
            {
                "button_id": "micro_power",
                "vietnamese_name": "Vi sóng",
                "function_description": "chọn mức công suất vi sóng",
                "manual_evidence": {"page": 4, "quote": "Nhấn Micro Power để chọn công suất."},
            }
        ]
    }
    described = describe_buttons(reply, button_ids=["micro_power"])
    assert described[0]["vietnamese_name"] == "Vi sóng"
    assert described[0]["manual_evidence"]["page"] == 4


def test_a_button_the_model_skipped_still_appears_with_blank_fields():
    # qc.py flags it as missing_name. Dropping it here would hide a button.
    described = describe_buttons({"buttons": []}, button_ids=["start", "stop"])
    assert [b["button_id"] for b in described] == ["start", "stop"]
    assert described[0]["vietnamese_name"] == ""
    assert described[0]["function_description"] == ""
    assert described[0]["manual_evidence"] is None


def test_a_button_the_model_invented_is_discarded():
    # detect.py decides which buttons exist. describe.py may not add to that list.
    reply = {
        "buttons": [
            {
                "button_id": "ghost",
                "vietnamese_name": "Ma",
                "function_description": "x",
            }
        ]
    }
    described = describe_buttons(reply, button_ids=["start"])
    assert [b["button_id"] for b in described] == ["start"]


def test_the_output_order_follows_the_detected_ids():
    reply = {"buttons": [
        {"button_id": "stop", "vietnamese_name": "Dừng", "function_description": "a"},
        {"button_id": "start", "vietnamese_name": "Bắt đầu", "function_description": "b"},
    ]}
    described = describe_buttons(reply, button_ids=["start", "stop"])
    assert [b["button_id"] for b in described] == ["start", "stop"]


def test_a_duplicate_id_in_the_reply_keeps_the_first():
    reply = {"buttons": [
        {"button_id": "start", "vietnamese_name": "Một", "function_description": "a"},
        {"button_id": "start", "vietnamese_name": "Hai", "function_description": "b"},
    ]}
    described = describe_buttons(reply, button_ids=["start"])
    assert len(described) == 1
    assert described[0]["vietnamese_name"] == "Một"


def test_a_reply_without_a_buttons_key_raises():
    with pytest.raises(ValueError, match="buttons"):
        describe_buttons({"items": []}, button_ids=["start"])


def test_write_descriptions_skips_null_ids_and_writes_the_file(tmp_path):
    # pipeline.py joins the manual document into a single string with
    # manual_full_text before calling write_descriptions; describe.py no longer
    # imports extract.py itself, so the test hands it the already-joined string.
    manual_text = "[page 1]\nStart."
    detections = {"detections": [
        {"button_id": "start", "label_text": "Start"},
        {"button_id": None, "label_text": ""},
    ]}

    class FakeClient:
        model = "fake-model"
        captured_prompt = ""

        def prompt_version(self, prompt):
            return "sha256:fake"

        def generate_json(self, prompt, *, image=None, mime_type="image/png"):
            FakeClient.captured_prompt = prompt
            assert image is None  # describe.py must never see the image
            return {"buttons": [{"button_id": "start", "vietnamese_name": "Bắt đầu",
                                 "function_description": "bắt đầu nấu",
                                 "manual_evidence": {"page": 1, "quote": "Start."}}]}

    out = tmp_path / "described.json"
    body = write_descriptions(manual_text, detections, out, client=FakeClient())

    assert json.loads(out.read_text(encoding="utf-8")) == body
    assert [b["button_id"] for b in body["buttons"]] == ["start"]
    assert "Start." in FakeClient.captured_prompt  # the manual text reached the prompt

    # The null-id button must never reach the model: no bullet line for it, and its
    # button_id (None -> "None") must not appear anywhere in the prompt's button listing.
    bullet_lines = [
        line for line in FakeClient.captured_prompt.splitlines() if line.startswith("- ")
    ]
    assert bullet_lines == ['- start: chữ in trên nút là "Start"']
    assert "None" not in FakeClient.captured_prompt
