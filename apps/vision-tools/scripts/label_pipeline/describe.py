"""Stage 3: manual text + detected ids -> Vietnamese names and descriptions.

This module does not know the image exists. detect.py owns which buttons exist;
describe.py may only fill in words for the ids it is handed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.label_pipeline.extract import manual_full_text
from scripts.label_pipeline.gemini_client import GeminiClient

DESCRIBE_PROMPT = """Bạn đang đọc sách hướng dẫn sử dụng của một thiết bị gia dụng.

Dưới đây là nội dung sách hướng dẫn, và danh sách các nút đã được phát hiện trên bảng
điều khiển. Với mỗi nút, hãy viết:

  - "vietnamese_name": tên ngắn gọn bằng tiếng Việt, dùng để đọc to cho người lớn tuổi.
    Không bao giờ chứa button_id thô (ví dụ "time_1_min").
  - "function_description": công dụng của nút, bằng tiếng Việt.
  - "manual_evidence": {{"page": <số trang>, "quote": "<câu trích nguyên văn từ sách>"}}
    Câu trích phải xuất hiện y nguyên trong nội dung sách bên dưới. Nếu sách không nói
    gì về nút này, đặt "manual_evidence": null và để mô tả trống.

Không bịa. Không thêm nút nào ngoài danh sách.

NỘI DUNG SÁCH:
{manual}

CÁC NÚT ĐÃ PHÁT HIỆN:
{buttons}

Trả về JSON:
{{"buttons": [{{"button_id": "...", "vietnamese_name": "...",
  "function_description": "...", "manual_evidence": {{"page": 1, "quote": "..."}}}}]}}
"""


def _blank(button_id: str) -> dict:
    return {
        "button_id": button_id,
        "vietnamese_name": "",
        "function_description": "",
        "manual_evidence": None,
    }


def describe_buttons(reply: dict, *, button_ids: list[str]) -> list[dict]:
    if "buttons" not in reply:
        raise ValueError(f"model reply has no 'buttons' key: {sorted(reply)}")

    by_id: dict[str, dict] = {}
    for item in reply["buttons"]:
        button_id = item.get("button_id")
        # detect.py decides which buttons exist; a first answer wins over a repeat.
        if button_id in button_ids and button_id not in by_id:
            by_id[button_id] = {
                "button_id": button_id,
                "vietnamese_name": str(item.get("vietnamese_name") or ""),
                "function_description": str(
                    item.get("function_description") or ""
                ),
                "manual_evidence": item.get("manual_evidence") or None,
            }
    # A button the model skipped still appears, blank, for qc.py to flag.
    return [by_id.get(button_id, _blank(button_id)) for button_id in button_ids]


def write_descriptions(
    manual_text: dict,
    detections: dict,
    out_path: Path,
    *,
    client: GeminiClient,
) -> dict:
    button_ids = [
        d["button_id"] for d in detections["detections"] if d.get("button_id")
    ]
    listing = "\n".join(
        f"- {d['button_id']}: chữ in trên nút là \"{d['label_text']}\""
        for d in detections["detections"]
        if d.get("button_id")
    )
    manual = manual_full_text(manual_text)
    prompt = DESCRIBE_PROMPT.format(manual=manual, buttons=listing)

    # The manual is inside the prompt, so the prompt hash already covers it. The salt
    # covers the id list, which is not otherwise part of the prompt template.
    salt = hashlib.sha256("|".join(button_ids).encode("utf-8")).digest()
    reply = client.generate_json(prompt, cache_salt=salt)

    body = {
        "model": client.model,
        "prompt_version": client.prompt_version(prompt),
        "buttons": describe_buttons(reply, button_ids=button_ids),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return body
