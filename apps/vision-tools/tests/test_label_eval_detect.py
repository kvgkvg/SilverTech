from __future__ import annotations

import pytest

from scripts.label_pipeline.eval_detect import evaluate, match_greedy


def box(x, y, size=100):
    return {"x": x, "y": y, "width": size, "height": size}


def det(button_id, x, y, size=100):
    return {"button_id": button_id, "bbox_template_coordinates": box(x, y, size)}


def test_a_perfect_match_scores_one_across_the_board():
    gold = [det("start", 0, 0), det("stop", 200, 0)]
    result = evaluate(list(gold), gold)
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert result["mean_iou"] == pytest.approx(1.0)
    assert result["id_accuracy"] == 1.0


def test_an_extra_detection_lowers_precision_but_not_recall():
    gold = [det("start", 0, 0)]
    detections = [det("start", 0, 0), det("ghost", 500, 500)]
    result = evaluate(detections, gold)
    assert result["precision"] == 0.5
    assert result["recall"] == 1.0


def test_a_missed_button_lowers_recall_but_not_precision():
    gold = [det("start", 0, 0), det("up", 200, 0)]
    result = evaluate([det("start", 0, 0)], gold)
    assert result["precision"] == 1.0
    assert result["recall"] == 0.5


def test_a_box_below_the_iou_threshold_is_not_a_match():
    gold = [det("start", 0, 0)]
    result = evaluate([det("start", 80, 0)], gold)  # IoU 0.11
    assert result["recall"] == 0.0
    assert result["matched"] == 0


def test_matching_is_one_to_one_and_takes_the_best_pair_first():
    gold = [det("start", 0, 0)]
    detections = [det("a", 10, 0), det("b", 0, 0)]  # b is the tighter box
    matches = [m for m in match_greedy(detections, gold) if m.gold_index is not None
               and m.detection_index is not None]
    assert len(matches) == 1
    assert detections[matches[0].detection_index]["button_id"] == "b"


def test_id_accuracy_counts_only_matched_pairs():
    gold = [det("start", 0, 0), det("stop", 200, 0)]
    detections = [det("start", 0, 0), det("wrong_name", 200, 0)]
    result = evaluate(detections, gold)
    assert result["recall"] == 1.0
    assert result["id_accuracy"] == 0.5


def test_numeric_gold_ids_are_excluded_from_id_accuracy():
    # Electrolux ids are "1".."11": position numbers off a manual diagram, not slugs
    # of on-panel text. No slug will ever equal "7", so scoring against them would
    # drag the metric down for a reason unrelated to the model.
    gold = [det("start", 0, 0), det("7", 200, 0)]
    detections = [det("start", 0, 0), det("power", 200, 0)]
    result = evaluate(detections, gold)
    assert result["id_accuracy"] == 1.0
    assert result["id_accuracy_excluded"] == 1


def test_id_accuracy_is_none_when_every_gold_id_is_numeric():
    gold = [det("1", 0, 0)]
    result = evaluate([det("power", 0, 0)], gold)
    assert result["id_accuracy"] is None
    assert result["id_accuracy_excluded"] == 1


def test_a_null_detected_id_never_matches_a_gold_id():
    gold = [det("up", 0, 0)]
    detections = [{"button_id": None, "bbox_template_coordinates": box(0, 0)}]
    result = evaluate(detections, gold)
    assert result["recall"] == 1.0  # the box is right
    assert result["id_accuracy"] == 0.0  # the id is absent


def test_mean_iou_averages_only_matched_pairs():
    # The second box overlaps by 80/100, giving IoU 8000/12000 = 2/3. It must stay
    # above the 0.5 match threshold, or there is nothing to average.
    gold = [det("start", 0, 0), det("stop", 500, 0)]
    detections = [det("start", 0, 0), det("stop", 520, 0)]
    result = evaluate(detections, gold)
    assert result["mean_iou"] == pytest.approx((1.0 + 2 / 3) / 2)


def test_an_empty_detection_list_scores_zero_without_dividing_by_zero():
    result = evaluate([], [det("start", 0, 0)])
    assert result["precision"] == 0.0
    assert result["recall"] == 0.0
    assert result["mean_iou"] == 0.0
    assert result["id_accuracy"] is None


def test_the_per_button_table_names_every_gold_button():
    # With n=27, one button is 4%. The aggregates alone would be self-deception.
    gold = [det("start", 0, 0), det("up", 500, 0)]
    result = evaluate([det("start", 0, 0)], gold)
    rows = {row["gold_id"]: row for row in result["per_button"]}
    assert set(rows) == {"start", "up"}
    assert rows["up"]["status"] == "missed"
    assert rows["start"]["status"] == "matched"
    assert rows["start"]["iou"] == pytest.approx(1.0)


def test_the_per_button_table_lists_extra_detections():
    gold = [det("start", 0, 0)]
    result = evaluate([det("start", 0, 0), det("ghost", 900, 900)], gold)
    extra = [row for row in result["per_button"] if row["status"] == "extra"]
    assert extra[0]["detected_id"] == "ghost"
    assert extra[0]["gold_id"] is None
