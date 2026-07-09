from __future__ import annotations

from scripts.label_pipeline.qc import run_qc

IMAGE = {"width": 1000, "height": 1000}
PANEL = {"x": 0, "y": 0, "width": 1000, "height": 1000}
MANUAL = "Nhấn nút Start để bắt đầu. Nhấn Stop để dừng."


def button(**overrides) -> dict:
    base = {
        "button_id": "start",
        "label_text": "Start",
        "vietnamese_name": "Bắt đầu",
        "function_description": "bắt đầu nấu",
        "manual_evidence": {"page": 1, "quote": "Nhấn nút Start để bắt đầu."},
        "bbox_template_coordinates": {"x": 100, "y": 100, "width": 100, "height": 100},
        "confidence": 0.9,
    }
    return {**base, **overrides}


def issues_for(buttons, **kwargs) -> list[list[str]]:
    checked, _report = run_qc(
        buttons, manual_text=MANUAL, image=IMAGE, panel_bbox=PANEL, **kwargs
    )
    return [b["qc"]["issues"] for b in checked]


def test_a_clean_button_passes():
    checked, report = run_qc([button()], manual_text=MANUAL, image=IMAGE, panel_bbox=PANEL)
    assert checked[0]["qc"] == {"status": "pass", "issues": [], "confidence": 0.9}
    assert report["counts"] == {"total": 1, "pass": 1, "flag": 0}


def test_no_rule_ever_drops_a_button():
    broken = [button(button_id=None), button(button_id="x", vietnamese_name=""), button()]
    checked, _ = run_qc(broken, manual_text=MANUAL, image=IMAGE, panel_bbox=PANEL)
    assert len(checked) == 3


def test_missing_id_is_flagged():
    assert "missing_id" in issues_for([button(button_id=None)])[0]
    assert "missing_id" in issues_for([button(button_id="  ")])[0]


def test_missing_name_is_flagged():
    assert "missing_name" in issues_for([button(vietnamese_name="")])[0]
    assert "missing_name" in issues_for([button(vietnamese_name="   ")])[0]


def test_raw_id_in_text_is_flagged():
    # Mirrors the API bug where the LLM echoed time_1_min into spoken text and gTTS
    # read it aloud as "tam gach duoi mot gach duoi min".
    bad = button(button_id="time_1_min", function_description="Nhấn time_1_min một lần.")
    assert "raw_id_in_text" in issues_for([bad])[0]


def test_raw_id_in_the_vietnamese_name_is_also_flagged():
    bad = button(button_id="time_1_min", vietnamese_name="time_1_min")
    assert "raw_id_in_text" in issues_for([bad])[0]


def test_a_single_word_id_that_is_a_real_vietnamese_word_is_not_flagged():
    # "up" as a substring of "Cúp điện" must not trip the rule; match on word bounds.
    ok = button(button_id="up", vietnamese_name="Tăng", function_description="Tăng thời gian.")
    assert "raw_id_in_text" not in issues_for([ok])[0]


def test_no_evidence_is_flagged_when_the_quote_is_not_in_the_manual():
    invented = button(manual_evidence={"page": 9, "quote": "Câu này không có trong sách."})
    assert "no_evidence" in issues_for([invented])[0]


def test_no_evidence_is_flagged_when_evidence_is_null():
    assert "no_evidence" in issues_for([button(manual_evidence=None)])[0]


def test_evidence_matching_ignores_surrounding_whitespace():
    ok = button(manual_evidence={"page": 1, "quote": "  Nhấn nút Start để bắt đầu.  "})
    assert "no_evidence" not in issues_for([ok])[0]


def test_no_evidence_is_flagged_when_the_quote_is_null_and_does_not_raise():
    bad = button(manual_evidence={"page": 1, "quote": None})
    assert "no_evidence" in issues_for([bad])[0]


def test_no_evidence_is_flagged_when_the_quote_is_not_a_string_and_does_not_raise():
    bad = button(manual_evidence={"page": 1, "quote": 123})
    assert "no_evidence" in issues_for([bad])[0]


def test_no_evidence_is_flagged_when_the_quote_is_whitespace_only():
    bad = button(manual_evidence={"page": 1, "quote": "   "})
    assert "no_evidence" in issues_for([bad])[0]


def test_low_confidence_is_flagged_against_the_threshold():
    assert "low_confidence" in issues_for([button(confidence=0.4)])[0]
    assert "low_confidence" not in issues_for([button(confidence=0.5)])[0]
    assert "low_confidence" in issues_for([button(confidence=0.6)], confidence_threshold=0.7)[0]


def test_bbox_out_of_bounds_is_flagged():
    over = button(bbox_template_coordinates={"x": 950, "y": 0, "width": 100, "height": 10})
    assert "bbox_out_of_bounds" in issues_for([over])[0]
    negative = button(bbox_template_coordinates={"x": -1, "y": 0, "width": 10, "height": 10})
    assert "bbox_out_of_bounds" in issues_for([negative])[0]


def test_a_zero_width_bbox_is_out_of_bounds():
    flat = button(bbox_template_coordinates={"x": 10, "y": 10, "width": 0, "height": 10})
    assert "bbox_out_of_bounds" in issues_for([flat])[0]


def test_bbox_degenerate_is_flagged_below_the_area_ratio():
    # 0.1% of 1000x1000 is 1000 px. A 30x30 box is 900.
    tiny = button(bbox_template_coordinates={"x": 10, "y": 10, "width": 30, "height": 30})
    assert "bbox_degenerate" in issues_for([tiny])[0]
    bbox_ok = {"x": 10, "y": 10, "width": 32, "height": 32}
    just_big_enough = button(bbox_template_coordinates=bbox_ok)
    assert "bbox_degenerate" not in issues_for([just_big_enough])[0]


def test_bbox_outside_panel_is_flagged_on_the_box_centre():
    panel = {"x": 0, "y": 0, "width": 500, "height": 500}
    outside = button(bbox_template_coordinates={"x": 600, "y": 600, "width": 100, "height": 100})
    checked, _ = run_qc([outside], manual_text=MANUAL, image=IMAGE, panel_bbox=panel)
    assert "bbox_outside_panel" in checked[0]["qc"]["issues"]


def test_bbox_outside_panel_is_skipped_when_there_is_no_panel():
    b = button(bbox_template_coordinates={"x": 600, "y": 600, "width": 100, "height": 100})
    checked, _ = run_qc([b], manual_text=MANUAL, image=IMAGE, panel_bbox=None)
    assert "bbox_outside_panel" not in checked[0]["qc"]["issues"]


def test_duplicate_id_flags_both_buttons_and_the_template():
    bbox = {"x": 500, "y": 500, "width": 100, "height": 100}
    twins = [button(), button(bbox_template_coordinates=bbox)]
    checked, report = run_qc(twins, manual_text=MANUAL, image=IMAGE, panel_bbox=PANEL)
    assert all("duplicate_id" in b["qc"]["issues"] for b in checked)
    assert any(i["id"] == "duplicate_id" for i in report["template_issues"])


def test_two_null_ids_are_not_duplicates_of_each_other():
    bbox = {"x": 500, "y": 500, "width": 100, "height": 100}
    nulls = [
        button(button_id=None),
        button(button_id=None, bbox_template_coordinates=bbox),
    ]
    checked, _ = run_qc(nulls, manual_text=MANUAL, image=IMAGE, panel_bbox=PANEL)
    assert all("duplicate_id" not in b["qc"]["issues"] for b in checked)


def test_bbox_overlap_flags_both_buttons_above_the_threshold():
    bbox_a = {"x": 100, "y": 100, "width": 100, "height": 100}
    bbox_b = {"x": 150, "y": 100, "width": 100, "height": 100}
    a = button(button_id="a", bbox_template_coordinates=bbox_a)
    b = button(button_id="b", bbox_template_coordinates=bbox_b)
    checked, report = run_qc([a, b], manual_text=MANUAL, image=IMAGE, panel_bbox=PANEL)
    assert all("bbox_overlap" in x["qc"]["issues"] for x in checked)
    overlap = next(i for i in report["template_issues"] if i["id"] == "bbox_overlap")
    assert set(overlap["button_ids"]) == {"a", "b"}


def test_boxes_below_the_overlap_threshold_are_not_flagged():
    bbox_a = {"x": 100, "y": 100, "width": 100, "height": 100}
    bbox_b = {"x": 190, "y": 100, "width": 100, "height": 100}
    a = button(button_id="a", bbox_template_coordinates=bbox_a)
    b = button(button_id="b", bbox_template_coordinates=bbox_b)
    checked, _ = run_qc([a, b], manual_text=MANUAL, image=IMAGE, panel_bbox=PANEL)
    assert all("bbox_overlap" not in x["qc"]["issues"] for x in checked)


def test_manual_button_missing_is_a_template_issue():
    # The manual names Stop; detect never found it. Only the manual can reveal this.
    checked, report = run_qc([button()], manual_text=MANUAL, image=IMAGE, panel_bbox=PANEL)
    missing = next(i for i in report["template_issues"] if i["id"] == "manual_button_missing")
    assert "stop" in missing["names"]
    assert checked[0]["qc"]["status"] == "pass"  # a template issue does not fail a button


def test_detected_not_in_manual_is_a_template_issue():
    extra = button(button_id="grill", label_text="Grill", vietnamese_name="Nướng",
                   manual_evidence=None)
    _checked, report = run_qc([button(), extra], manual_text=MANUAL, image=IMAGE, panel_bbox=PANEL)
    not_in_manual = next(
        i for i in report["template_issues"]
        if i["id"] == "detected_not_in_manual"
    )
    assert not_in_manual["button_ids"] == ["grill"]


def test_the_report_counts_passes_and_flags():
    bbox = {"x": 500, "y": 500, "width": 100, "height": 100}
    evidence = {"page": 1, "quote": "Nhấn Stop để dừng."}
    _checked, report = run_qc(
        [button(), button(button_id="stop", vietnamese_name="",
                          bbox_template_coordinates=bbox,
                          manual_evidence=evidence)],
        manual_text=MANUAL, image=IMAGE, panel_bbox=PANEL,
    )
    assert report["counts"] == {"total": 2, "pass": 1, "flag": 1}


def test_issues_are_sorted_so_the_report_is_stable():
    # Asserting the exact list, not `== sorted(itself)`, which would pass whatever
    # qc.py returned. The quote is in the manual, so no_evidence must not appear.
    bad = button(button_id="", vietnamese_name="", confidence=0.1)
    assert issues_for([bad])[0] == ["low_confidence", "missing_id", "missing_name"]
