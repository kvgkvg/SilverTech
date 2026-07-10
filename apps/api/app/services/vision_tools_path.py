# apps/api/app/services/vision_tools_path.py
from __future__ import annotations

import sys

from app.storage.database import ROOT

# vision-tools runs via path, not install (see CLAUDE.md); make its scripts importable.
_VISION_TOOLS = ROOT / "apps" / "vision-tools"


def ensure_vision_tools_on_path() -> None:
    entry = str(_VISION_TOOLS)
    if entry not in sys.path:
        sys.path.insert(0, entry)
