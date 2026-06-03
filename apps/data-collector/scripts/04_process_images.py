from __future__ import annotations

import json
import shutil
from pathlib import Path

import imagehash
from PIL import Image

from src.config import get_settings
from src.process.brand import detect_brand
from src.process.ocr import run_ocr


def main() -> None:
    s = get_settings()
    in_path = s.collected_dir / "metadata_downloaded.jsonl"
    records = [json.loads(l) for l in in_path.read_text().splitlines() if l.strip()]

    unverified = s.collected_dir / "unverified"
    unverified.mkdir(parents=True, exist_ok=True)
    out = s.collected_dir / "metadata_slice1.jsonl"

    with out.open("w") as f:
        for rec in records:
            if rec.get("status") != "validated" or not rec.get("image_path"):
                f.write(json.dumps(rec) + "\n")
                continue
            path = Path(rec["image_path"])
            ocr_lines = run_ocr(path)
            brand, has_logo = detect_brand(ocr_lines)
            rec["ocr_text"] = ocr_lines
            rec["ocr_joined"] = " ".join(ocr_lines)
            rec["brand"] = brand
            rec["brand_source"] = "ocr" if brand else None
            rec["has_visible_logo"] = has_logo
            try:
                with Image.open(path) as img:
                    rec["phash"] = str(imagehash.phash(img))
            except Exception:  # noqa: BLE001
                rec["phash"] = None
            rec["status"] = "ocr_done"
            if not has_logo:
                shutil.copy(str(path), str(unverified / path.name))
            f.write(json.dumps(rec) + "\n")

    print(f"[04] wrote {len(records)} records -> {out}")


if __name__ == "__main__":
    main()
