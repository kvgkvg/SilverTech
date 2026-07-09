"""Stage 2: panel image -> detections.json.

This module does not know the manual exists. It sees pixels and returns boxes.
It meets describe.py only through button_id.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from scripts.label_pipeline.gemini_client import GeminiClient
from scripts.label_pipeline.geometry import to_bbox

DETECT_PROMPT = """You are looking at a photograph of a household appliance control panel.

Find every button, knob, dial, and touch key on the panel.

For each one return:
  - "label_text": the text printed on or immediately beside the control, copied exactly
    as it appears. If the control carries no text at all (an icon-only arrow, for
    example), return an empty string. Never invent a name.
  - "box_2d": [ymin, xmin, ymax, xmax], normalized to 0-1000.
  - "confidence": your confidence between 0 and 1.

Also return "regions":
  - "logo": box_2d around the manufacturer's brand logo.
  - "panel": box_2d around the whole control panel.

Return JSON:
{"detections": [{"label_text": "...", "box_2d": [0,0,0,0], "confidence": 0.0}],
 "regions": {"logo": [0,0,0,0], "panel": [0,0,0,0]}}
"""

MIME_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


def slug(value: str) -> str:
    """Python twin of slug() in label_web/app.js.

    The two must agree or ids diverge.
    """
    text = unicodedata.normalize("NFD", str(value or "").strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _region(
    box_2d: object, width: int, height: int
) -> dict[str, int] | None:
    if not isinstance(box_2d, list) or len(box_2d) != 4:
        return None
    return to_bbox(box_2d, width=width, height=height)


def detect_buttons(reply: dict, *, width: int, height: int) -> dict:
    if "detections" not in reply:
        raise ValueError(
            f"model reply has no 'detections' key: {sorted(reply)}"
        )

    detections: list[dict] = []
    dropped: list[dict] = []
    for item in reply["detections"]:
        label_text = str(item.get("label_text") or "")
        box_2d = item.get("box_2d")
        if box_2d is None:
            dropped.append({"label_text": label_text, "reason": "no box_2d"})
            continue
        try:
            bbox = to_bbox(box_2d, width=width, height=height)
        except (ValueError, TypeError) as exc:
            dropped.append(
                {"label_text": label_text, "reason": f"bad box_2d: {exc}"}
            )
            continue
        button_id = slug(label_text) or None
        detections.append(
            {
                "button_id": button_id,
                "label_text": label_text,
                "box_2d": list(box_2d),
                "bbox_template_coordinates": bbox,
                # Absent confidence is not evidence of correctness.
                "confidence": float(item.get("confidence") or 0.0),
            }
        )

    regions = reply.get("regions") or {}
    return {
        "image": {"width": width, "height": height},
        "detections": detections,
        "dropped": dropped,
        "regions": {
            "logo": _region(regions.get("logo"), width, height),
            "panel": _region(regions.get("panel"), width, height),
        },
    }


def write_detections(
    image_path: Path, out_path: Path, *, client: GeminiClient
) -> dict:
    from PIL import Image

    with Image.open(image_path) as image:
        width, height = image.size
    image_bytes = image_path.read_bytes()
    mime = MIME_TYPES.get(image_path.suffix.lower(), "image/png")

    # A failed detect fails the run: with no boxes there is nothing to emit.
    reply = client.generate_json(
        DETECT_PROMPT, image=image_bytes, mime_type=mime
    )
    body = detect_buttons(reply, width=width, height=height)
    body["image"]["path"] = str(image_path)
    body["model"] = client.model
    body["prompt_version"] = client.prompt_version(DETECT_PROMPT)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return body
