from __future__ import annotations

from typing import Any


class LLMService:
    def generate(self, user_query: str, template: dict[str, Any]) -> dict[str, Any]:
        query = user_query.lower()
        buttons = {b["button_id"]: b for b in template["buttons"]}
        if "nhiệt" in query or "nhiet" in query:
            button_id = "temp_up" if "temp_up" in buttons else next(iter(buttons))
            instruction = "Nhấn nút tăng nhiệt độ một lần."
            intent = "adjust_temperature"
        elif "sấy" in query or "say" in query:
            button_id = "dry_mode" if "dry_mode" in buttons else next(iter(buttons))
            instruction = "Nhấn nút Sấy để chọn chế độ sấy."
            intent = "dry_mode"
        elif "bắt đầu" in query or "bat dau" in query or "start" in query:
            button_id = "start_pause" if "start_pause" in buttons else next(iter(buttons))
            instruction = "Nhấn nút Bắt đầu để chạy chương trình."
            intent = "find_start"
        else:
            button_id = "quick_wash" if "quick_wash" in buttons else next(iter(buttons))
            instruction = "Nhấn nút Giặt nhanh để chọn chương trình giặt nhanh."
            intent = "quick_wash"
        return {
            "intent": intent,
            "steps": [
                {
                    "step_number": 1,
                    "instruction_vi": instruction,
                    "button_id": button_id,
                    "expected_result": "Máy chọn đúng chức năng trên bảng điều khiển.",
                }
            ],
            "safety_note": None,
        }
