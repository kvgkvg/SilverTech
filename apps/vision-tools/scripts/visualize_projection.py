from __future__ import annotations

import json
from pathlib import Path


def save_visualization(projected: dict, output_path: str | Path) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(projected, ensure_ascii=False, indent=2), encoding="utf-8")
