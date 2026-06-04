from __future__ import annotations

from typing import Any


class LLMService:
    def generate(self, user_query: str, template: dict[str, Any]) -> dict[str, Any]:
        query = user_query.lower()
        if template["id"] == "template_panasonic_microwave_nn_gt35hm_v1":
            if "nướng" in query or "nuong" in query:
                return {
                    "intent": "grill_meat",
                    "steps": [
                        {
                            "step_number": 1,
                            "instruction_vi": "Nhấn nút Nướng để chọn chế độ nướng.",
                            "button_id": "grill",
                            "expected_result": "Lò chuyển sang chế độ nướng.",
                        },
                        {
                            "step_number": 2,
                            "instruction_vi": "Nhấn nút 10 phút để cài thời gian nướng.",
                            "button_id": "time_10_min",
                            "expected_result": "Thời gian nướng được đặt thêm 10 phút.",
                        },
                        {
                            "step_number": 3,
                            "instruction_vi": "Nhấn nút Khởi động để bắt đầu nướng.",
                            "button_id": "start",
                            "expected_result": "Lò bắt đầu nướng thịt.",
                        },
                    ],
                    "safety_note": "Dùng dụng cụ chịu nhiệt và không dùng hộp nhựa khi nướng.",
                }
            if "rã đông" in query or "ra dong" in query:
                return {
                    "intent": "defrost_meat",
                    "steps": [
                        {
                            "step_number": 1,
                            "instruction_vi": "Nhấn nút Rã đông để chọn chế độ rã đông thịt.",
                            "button_id": "turbo_defrost",
                            "expected_result": "Lò chuyển sang chế độ rã đông.",
                        },
                        {
                            "step_number": 2,
                            "instruction_vi": "Nhấn nút Tăng hoặc Giảm để chỉnh khối lượng thịt.",
                            "button_id": "up",
                            "expected_result": "Khối lượng rã đông được điều chỉnh.",
                        },
                        {
                            "step_number": 3,
                            "instruction_vi": "Nhấn nút Khởi động để bắt đầu rã đông.",
                            "button_id": "start",
                            "expected_result": "Lò bắt đầu rã đông thịt.",
                        },
                    ],
                    "safety_note": "Sau khi rã đông, nên nấu thịt ngay và kiểm tra phần giữa đã mềm chưa.",
                }
            if "hẹn giờ" in query or "hen gio" in query or "30 phút" in query or "30 phut" in query:
                return {
                    "intent": "set_timer_30_minutes",
                    "steps": [
                        {
                            "step_number": 1,
                            "instruction_vi": "Nhấn nút Hẹn giờ/Đồng hồ.",
                            "button_id": "time_clock",
                            "expected_result": "Lò chuyển sang chế độ cài hẹn giờ.",
                        },
                        {
                            "step_number": 2,
                            "instruction_vi": "Nhấn nút 10 phút ba lần để cài 30 phút.",
                            "button_id": "time_10_min",
                            "expected_result": "Màn hình hiển thị thời gian 30 phút.",
                        },
                        {
                            "step_number": 3,
                            "instruction_vi": "Nhấn nút Khởi động để bắt đầu đếm giờ.",
                            "button_id": "start",
                            "expected_result": "Lò bắt đầu đếm ngược 30 phút.",
                        },
                    ],
                    "safety_note": "Khi chỉ dùng hẹn giờ, lò đếm thời gian và không nấu thức ăn.",
                }

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
