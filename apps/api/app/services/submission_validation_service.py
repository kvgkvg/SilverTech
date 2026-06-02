from __future__ import annotations


def validate_panel_submission(image_url: str, proposed_labels_json: dict) -> None:
    if not image_url:
        raise ValueError("image_url is required")
    if not proposed_labels_json:
        raise ValueError("proposed labels are required")
    forbidden = ["person", "face", "private", "room"]
    if any(token in image_url.lower() for token in forbidden):
        raise ValueError("submission image must be limited to appliance control panel content")
