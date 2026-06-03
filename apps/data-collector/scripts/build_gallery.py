from __future__ import annotations

import json

from src.config import get_settings
from src.report.gallery import render_gallery


def main() -> None:
    s = get_settings()
    in_path = s.collected_dir / "metadata_slice1.jsonl"
    records = [json.loads(l) for l in in_path.read_text().splitlines() if l.strip()]
    # Make image paths relative to the gallery file location (collected_dir).
    for r in records:
        if r.get("image_path"):
            r["image_path"] = r["image_path"].split("collected/")[-1]
    html = render_gallery(records)
    out = s.collected_dir / "gallery.html"
    out.write_text(html)
    print(f"[gallery] wrote {len(records)} records -> {out}")


if __name__ == "__main__":
    main()
