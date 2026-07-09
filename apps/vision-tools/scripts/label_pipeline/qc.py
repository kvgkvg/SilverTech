"""Stage 4: the single place that decides whether a button is trustworthy.

Flags, never deletes. Every detected button reaches the draft, because a button
silently dropped here is a button nobody reviews.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict

from scripts.label_pipeline.geometry import bbox_area, center, iou

CONFIDENCE_THRESHOLD = 0.5
IOU_THRESHOLD = 0.3
MIN_AREA_RATIO = 0.001  # 0.1% of the image


def _fold(text: str) -> str:
    """Lowercase, strip diacritics. Used to compare model text against manual text."""
    folded = unicodedata.normalize("NFD", str(text or "").lower())
    return "".join(ch for ch in folded if not unicodedata.combining(ch))


def _mentions_raw_id(text: str, button_id: str) -> bool:
    # Word bounds, so "up" inside "Cúp điện" does not trip the rule.
    return re.search(rf"\b{re.escape(button_id)}\b", text, re.IGNORECASE) is not None


def _check_button(
    button: dict,
    *,
    manual_text: str,
    image: dict,
    panel_bbox: dict | None,
    confidence_threshold: float,
    min_area_ratio: float,
) -> list[str]:
    issues: list[str] = []
    button_id = (button.get("button_id") or "").strip()
    name = (button.get("vietnamese_name") or "").strip()

    if not button_id:
        issues.append("missing_id")
    if not name:
        issues.append("missing_name")

    if button_id:
        blob = f"{name} {button.get('function_description') or ''}"
        if _mentions_raw_id(blob, button_id):
            issues.append("raw_id_in_text")

    evidence = button.get("manual_evidence")
    quote = (evidence or {}).get("quote", "").strip() if isinstance(evidence, dict) else ""
    if not quote or _fold(quote) not in _fold(manual_text):
        issues.append("no_evidence")

    if float(button.get("confidence") or 0.0) < confidence_threshold:
        issues.append("low_confidence")

    box = button.get("bbox_template_coordinates") or {}
    if _out_of_bounds(box, image):
        issues.append("bbox_out_of_bounds")
    elif bbox_area(box) < min_area_ratio * image["width"] * image["height"]:
        issues.append("bbox_degenerate")

    if panel_bbox and box and not _center_inside(box, panel_bbox):
        issues.append("bbox_outside_panel")

    return issues


def _out_of_bounds(box: dict, image: dict) -> bool:
    if not box or box.get("width", 0) <= 0 or box.get("height", 0) <= 0:
        return True
    return (
        box["x"] < 0
        or box["y"] < 0
        or box["x"] + box["width"] > image["width"]
        or box["y"] + box["height"] > image["height"]
    )


def _center_inside(box: dict, panel: dict) -> bool:
    cx, cy = center(box)
    return (
        panel["x"] <= cx <= panel["x"] + panel["width"]
        and panel["y"] <= cy <= panel["y"] + panel["height"]
    )


def _manual_names(manual_text: str) -> set[str]:
    """Capitalised control names the manual mentions, folded and slugged, roughly.

    Deliberately crude: this feeds a flag, not a decision. Manuals omit minor buttons
    and photos crop corners, so both directions of this comparison only warn.
    """
    words = re.findall(r"\b[A-Z][a-zA-Z0-9]*(?:[ /-][A-Z][a-zA-Z0-9]*)*\b", manual_text)
    return {re.sub(r"[^a-z0-9]+", "_", w.lower()).strip("_") for w in words if len(w) > 1}


def run_qc(
    buttons: list[dict],
    *,
    manual_text: str,
    image: dict,
    panel_bbox: dict | None,
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
    iou_threshold: float = IOU_THRESHOLD,
    min_area_ratio: float = MIN_AREA_RATIO,
) -> tuple[list[dict], dict]:
    per_button: list[list[str]] = [
        _check_button(
            b,
            manual_text=manual_text,
            image=image,
            panel_bbox=panel_bbox,
            confidence_threshold=confidence_threshold,
            min_area_ratio=min_area_ratio,
        )
        for b in buttons
    ]
    template_issues: list[dict] = []

    # duplicate_id — a null id is not a duplicate of another null id.
    seen: dict[str, list[int]] = defaultdict(list)
    for index, b in enumerate(buttons):
        button_id = (b.get("button_id") or "").strip()
        if button_id:
            seen[button_id].append(index)
    duplicates = {k: v for k, v in seen.items() if len(v) > 1}
    if duplicates:
        template_issues.append({"id": "duplicate_id", "button_ids": sorted(duplicates)})
        for indices in duplicates.values():
            for index in indices:
                per_button[index].append("duplicate_id")

    # bbox_overlap
    overlapping: set[int] = set()
    pairs: list[list[str | None]] = []
    for i in range(len(buttons)):
        for j in range(i + 1, len(buttons)):
            box_i = buttons[i].get("bbox_template_coordinates") or {}
            box_j = buttons[j].get("bbox_template_coordinates") or {}
            if box_i and box_j and iou(box_i, box_j) > iou_threshold:
                overlapping.update({i, j})
                pairs.append([buttons[i].get("button_id"), buttons[j].get("button_id")])
    if overlapping:
        template_issues.append(
            {
                "id": "bbox_overlap",
                "button_ids": sorted(str(buttons[i].get("button_id")) for i in overlapping),
                "pairs": pairs,
            }
        )
        for index in overlapping:
            per_button[index].append("bbox_overlap")

    # manual_button_missing / detected_not_in_manual — why the pipeline needs both inputs.
    detected_ids = {(b.get("button_id") or "").strip() for b in buttons} - {""}
    named_in_manual = _manual_names(manual_text)
    missing = sorted(named_in_manual - detected_ids - {"", "the", "a"})
    unseen = sorted(
        button_id for button_id in detected_ids if button_id not in named_in_manual
    )
    if missing:
        template_issues.append({"id": "manual_button_missing", "names": missing})
    if unseen:
        template_issues.append({"id": "detected_not_in_manual", "button_ids": unseen})

    checked: list[dict] = []
    for b, issues in zip(buttons, per_button, strict=True):
        sorted_issues = sorted(set(issues))
        checked.append(
            {
                **b,
                "qc": {
                    "status": "pass" if not sorted_issues else "flag",
                    "issues": sorted_issues,
                    "confidence": float(b.get("confidence") or 0.0),
                },
            }
        )

    flagged = sum(1 for b in checked if b["qc"]["status"] == "flag")
    report = {
        "template_issues": template_issues,
        "counts": {"total": len(checked), "pass": len(checked) - flagged, "flag": flagged},
    }
    return checked, report
