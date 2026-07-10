"""Composes the four stages and writes <template_code>.draft.json + qc_report.json.

The pipeline never overwrites a reviewed label file. It writes a draft; a human
renames it after review. Nothing here writes to apps/api/silvertech.sqlite3.

Usage:
    PYTHONPATH=apps/vision-tools python -m scripts.label_pipeline.pipeline \\
      --manual data/manuals/panasonic_nn_gt35hm.pdf \\
      --image  data/templates/panasonic_microwave_nn_gt35hm.png \\
      --brand Panasonic --model-name NN-GT35HM --appliance-type microwave \\
      --display-name "Lò vi sóng Panasonic NN-GT35HM" \\
      --out data/templates/labels/panasonic_microwave_nn_gt35hm_v1.draft.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.label_pipeline.describe import write_descriptions
from scripts.label_pipeline.detect import slug, write_detections
from scripts.label_pipeline.extract import manual_full_text, write_manual_text
from scripts.label_pipeline.gemini_client import (
    DEFAULT_MODEL,
    GeminiClient,
    GeminiError,
    load_api_key,
)
from scripts.label_pipeline.qc import run_qc

DEFAULT_BUTTON_TYPE = "touch"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_draft(
    *,
    detections: dict,
    qc_buttons: list[dict],
    device: dict,
    template: dict,
) -> dict:
    rows: list[dict] = []
    for index, button in enumerate(qc_buttons):
        button_id = (button.get("button_id") or "").strip()
        suffix = button_id or f"unnamed_{index}"
        rows.append(
            {
                # Row id must match what label_web/app.js:286 recomputes on save:
                # `btn_${templateId without "template_" prefix}_${button_id}`.
                "id": f"btn_{template['template_code']}_{suffix}",
                "template_id": template["id"],
                "button_id": button_id,
                "label": button.get("label_text") or button_id,
                "vietnamese_name": button.get("vietnamese_name", ""),
                "function_description": button.get("function_description", ""),
                "bbox_template_coordinates": button["bbox_template_coordinates"],
                "polygon_template_coordinates": None,
                "button_type": button.get("button_type") or DEFAULT_BUTTON_TYPE,
                "created_at": _now(),
                "updated_at": _now(),
                "qc": button["qc"],
            }
        )
    regions = detections.get("regions") or {}
    return {
        "device": {**device, "created_at": _now(), "updated_at": _now()},
        "template": {
            "feature_descriptor_path": None,
            **template,
            "logo_bbox": regions.get("logo"),
            "panel_bbox": regions.get("panel"),
            "created_at": _now(),
            "updated_at": _now(),
        },
        "buttons": rows,
    }


def _merge(detections: dict, described: dict) -> list[dict]:
    # Only key on truthy button_id: icon-only buttons carry button_id=None, and a
    # None key here would let every null-id detection collide on the same lookup
    # and inherit whichever description was described last.
    by_id = {b["button_id"]: b for b in described["buttons"] if b.get("button_id")}
    merged: list[dict] = []
    for detection in detections["detections"]:
        button_id = detection["button_id"]
        description = by_id.get(button_id, {}) if button_id else {}
        merged.append(
            {
                "button_id": detection["button_id"],
                "label_text": detection["label_text"],
                "bbox_template_coordinates": detection["bbox_template_coordinates"],
                "confidence": detection["confidence"],
                "vietnamese_name": description.get("vietnamese_name", ""),
                "function_description": description.get("function_description", ""),
                "manual_evidence": description.get("manual_evidence"),
            }
        )
    return merged


def run(args: argparse.Namespace, *, client: GeminiClient) -> dict:
    out_path = Path(args.out)
    work_dir = out_path.parent / ".pipeline" / Path(args.image).stem
    work_dir.mkdir(parents=True, exist_ok=True)

    manual_text = write_manual_text(
        Path(args.manual), work_dir / "manual_text.json", client=client
    )
    detections = write_detections(
        Path(args.image), work_dir / "detections.json", client=client
    )
    described = write_descriptions(
        manual_text, detections, work_dir / "described.json", client=client
    )

    qc_buttons, report = run_qc(
        _merge(detections, described),
        manual_text=manual_full_text(manual_text),
        image=detections["image"],
        panel_bbox=(detections.get("regions") or {}).get("panel"),
        confidence_threshold=args.confidence_threshold,
    )

    template_code = args.template_code or (
        slug(f"{args.brand} {args.appliance_type} {args.model_name}") + "_v1"
    )
    device_slug = template_code.removesuffix("_v1")
    device = {
        "id": f"device_{device_slug}",
        "brand": args.brand,
        "appliance_type": args.appliance_type,
        "model_name": args.model_name,
        "display_name": args.display_name or f"{args.brand} {args.model_name}",
        "status": "active",
    }
    template = {
        "id": f"template_{template_code}",
        "device_id": device["id"],
        "template_code": template_code,
        "template_image_url": args.image,
        "feature_descriptor_path": None,
        "version": 1,
        "status": "draft",
    }

    draft = build_draft(
        detections=detections, qc_buttons=qc_buttons, device=device, template=template,
    )

    # Never overwrite a reviewed label file.
    if out_path.exists() and not out_path.name.endswith(".draft.json"):
        raise SystemExit(f"refusing to overwrite reviewed label file {out_path}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")

    report_path = out_path.with_name(out_path.name.replace(".draft.json", ".qc_report.json"))
    report = {**report, "draft": str(out_path), "model": client.model}
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    counts = report["counts"]
    print(f"{out_path}: {counts['total']} buttons, {counts['flag']} flagged")
    for issue in report["template_issues"]:
        print(f"  template: {issue['id']}")
    return draft


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manual", required=True, help="appliance manual PDF")
    parser.add_argument("--image", required=True, help="control panel image")
    parser.add_argument("--out", required=True, help="path ending in .draft.json")
    parser.add_argument("--brand", required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--appliance-type", required=True)
    parser.add_argument("--display-name", default=None)
    parser.add_argument("--template-code", default=None)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--confidence-threshold", type=float, default=0.5)
    args = parser.parse_args(argv)

    if not args.out.endswith(".draft.json"):
        parser.error("--out must end in .draft.json; a human renames it after review")

    try:
        client = GeminiClient(api_key=load_api_key(), model=args.model)
        run(args, client=client)
    except (GeminiError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
