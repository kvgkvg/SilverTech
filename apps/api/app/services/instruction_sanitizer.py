from __future__ import annotations

import re
from typing import Any


def humanize_button_ids(text: str, buttons: list[dict[str, Any]]) -> str:
    """Rewrite raw `button_id` tokens inside an instruction as their Vietnamese names.

    The LLM sometimes echoes the identifier it was given (`time_1_min`) straight
    into `instruction_vi`. On screen that is merely ugly; through TTS it becomes
    unusable, because gTTS reads it out as "tam gạch dưới một gạch dưới min".
    """
    pairs = [
        (b["button_id"], b["vietnamese_name"])
        for b in buttons
        if b.get("button_id") and b.get("vietnamese_name")
    ]
    if not pairs:
        return text
    # Longest id first so `stop_reset` is not partially matched as `stop`.
    pairs.sort(key=lambda pair: len(pair[0]), reverse=True)
    names = {button_id.lower(): name for button_id, name in pairs}
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(button_id) for button_id, _ in pairs) + r")\b",
        re.IGNORECASE,
    )
    return pattern.sub(lambda match: names[match.group(1).lower()], text)
