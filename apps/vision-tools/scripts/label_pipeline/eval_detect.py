"""Measure detect.py against the two reviewed label files.

Run by hand, never in CI: CI calling the Gemini API would burn the free-tier quota.

Precision, recall and mean IoU measure three different things. A model can reach 100%
recall with a mean IoU of 0.55 -- it sees every button and boxes them loosely.
Collapsing them into one score hides that.

Gold set: Panasonic (16 buttons) + Electrolux (11) = 27. Electrolux's button_ids are
"1".."11" -- position numbers from a manual diagram, not slugs of on-panel text. They
are excluded from id_accuracy, and the excluded count is printed so the number is never
read as though it covered all 27.

Usage:
    PYTHONPATH=apps/vision-tools python -m scripts.label_pipeline.eval_detect \\
      --detections .cache/detections.json \\
      --gold data/templates/labels/panasonic_microwave_nn_gt35hm_v1.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import NamedTuple

from scripts.label_pipeline.geometry import iou

IOU_THRESHOLD = 0.5


class Match(NamedTuple):
    detection_index: int | None
    gold_index: int | None
    score: float


def _is_positional_id(button_id: str) -> bool:
    """An id like "7" names a diagram callout, not any text printed on the panel."""
    return bool(re.fullmatch(r"\d+", str(button_id or "").strip()))


def match_greedy(
    detections: list[dict], gold: list[dict], *, threshold: float = IOU_THRESHOLD
) -> list[Match]:
    pairs = sorted(
        (
            (iou(d["bbox_template_coordinates"], g["bbox_template_coordinates"]), di, gi)
            for di, d in enumerate(detections)
            for gi, g in enumerate(gold)
        ),
        reverse=True,
    )
    used_d: set[int] = set()
    used_g: set[int] = set()
    matches: list[Match] = []
    for score, di, gi in pairs:
        if score <= threshold or di in used_d or gi in used_g:
            continue
        used_d.add(di)
        used_g.add(gi)
        matches.append(Match(di, gi, score))
    matches += [Match(None, gi, 0.0) for gi in range(len(gold)) if gi not in used_g]
    matches += [Match(di, None, 0.0) for di in range(len(detections)) if di not in used_d]
    return matches


def evaluate(
    detections: list[dict], gold: list[dict], *, threshold: float = IOU_THRESHOLD
) -> dict:
    matches = match_greedy(detections, gold, threshold=threshold)
    matched = [m for m in matches if m.detection_index is not None and m.gold_index is not None]

    id_hits = 0
    id_scored = 0
    excluded = sum(1 for g in gold if _is_positional_id(g["button_id"]))
    per_button: list[dict] = []

    for m in matches:
        gold_button = gold[m.gold_index] if m.gold_index is not None else None
        detection = detections[m.detection_index] if m.detection_index is not None else None
        if gold_button is not None and detection is not None:
            status = "matched"
            if not _is_positional_id(gold_button["button_id"]):
                id_scored += 1
                id_hits += int(detection["button_id"] == gold_button["button_id"])
        elif gold_button is not None:
            status = "missed"
        else:
            status = "extra"
        per_button.append(
            {
                "gold_id": gold_button["button_id"] if gold_button else None,
                "detected_id": detection["button_id"] if detection else None,
                "iou": round(m.score, 3),
                "status": status,
            }
        )

    per_button.sort(key=lambda row: (row["status"] != "matched", row["gold_id"] or "~"))
    return {
        "threshold": threshold,
        "gold_count": len(gold),
        "detected_count": len(detections),
        "matched": len(matched),
        "precision": len(matched) / len(detections) if detections else 0.0,
        "recall": len(matched) / len(gold) if gold else 0.0,
        "mean_iou": sum(m.score for m in matched) / len(matched) if matched else 0.0,
        "id_accuracy": (id_hits / id_scored) if id_scored else None,
        "id_accuracy_scored": id_scored,
        "id_accuracy_excluded": excluded,
        "per_button": per_button,
    }


def _print(result: dict) -> None:
    print(f"gold {result['gold_count']}  detected {result['detected_count']}  "
          f"matched {result['matched']}  @IoU>{result['threshold']}")
    print(f"precision {result['precision']:.2f}   recall {result['recall']:.2f}   "
          f"mean IoU {result['mean_iou']:.2f}")
    if result["id_accuracy"] is None:
        print(f"button_id accuracy: n/a ({result['id_accuracy_excluded']} positional gold ids)")
    else:
        print(f"button_id accuracy {result['id_accuracy']:.2f} "
              f"over {result['id_accuracy_scored']} pairs "
              f"({result['id_accuracy_excluded']} positional gold ids excluded)")
    print()
    print(f"{'gold_id':<20} {'detected_id':<20} {'IoU':>6}  status")
    for row in result["per_button"]:
        print(f"{str(row['gold_id']):<20} {str(row['detected_id']):<20} "
              f"{row['iou']:>6.3f}  {row['status']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--detections", required=True, help="detections.json from detect.py")
    parser.add_argument("--gold", required=True, help="a reviewed label JSON file")
    parser.add_argument("--threshold", type=float, default=IOU_THRESHOLD)
    args = parser.parse_args(argv)

    detections = json.loads(Path(args.detections).read_text(encoding="utf-8"))["detections"]
    gold = json.loads(Path(args.gold).read_text(encoding="utf-8"))["buttons"]
    _print(evaluate(detections, gold, threshold=args.threshold))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
