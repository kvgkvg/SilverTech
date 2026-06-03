from __future__ import annotations

import json
import shutil
from pathlib import Path

from src.config import get_settings
from src.download.downloader import download_many
from src.process.validator import validate_image


def main() -> None:
    s = get_settings()
    cand_path = s.collected_dir / "candidates.jsonl"
    candidates = [json.loads(l) for l in cand_path.read_text().splitlines() if l.strip()]

    raw_images = s.collected_dir / "raw" / "images"
    raw_images.mkdir(parents=True, exist_ok=True)

    urls_dests = [(c["image_url"], raw_images / f"{c['candidate_id']}.jpg") for c in candidates]
    results = download_many(urls_dests, s.user_agent, s.request_timeout)

    report = {"total": len(candidates), "downloaded": 0, "validated": 0, "rejected": {}}
    by_id = {c["candidate_id"]: c for c in candidates}
    out = s.collected_dir / "metadata_downloaded.jsonl"

    with out.open("w") as f:
        for cand, res in zip(candidates, results):
            rec = dict(cand)
            if not res["ok"]:
                rec["status"] = "rejected"
                rec["reject_reason"] = "download_fail"
                _reject_count(report, "download_fail")
                _move_reject(s, None, "download_fail")  # nothing to move; count only
                f.write(json.dumps(rec) + "\n")
                continue
            report["downloaded"] += 1
            dest = Path(res["path"])
            v = validate_image(
                dest, s.min_image_width, s.min_image_height,
                s.min_image_file_size_kb, s.max_aspect_ratio,
            )
            rec["image_path"] = str(dest)
            rec["file_size"] = res["file_size"]
            rec["image_width"] = v["width"]
            rec["image_height"] = v["height"]
            if not v["ok"]:
                rec["status"] = "rejected"
                rec["reject_reason"] = v["reason"]
                _reject_count(report, v["reason"])
                _move_reject(s, dest, v["reason"])
                rec["image_path"] = None
            else:
                rec["status"] = "validated"
                report["validated"] += 1
            f.write(json.dumps(rec) + "\n")

    (s.collected_dir / "download_report.json").write_text(json.dumps(report, indent=2))
    print(f"[03] {report}")


def _reject_count(report: dict, reason: str) -> None:
    report["rejected"][reason] = report["rejected"].get(reason, 0) + 1


def _move_reject(s, dest, reason: str) -> None:
    if dest is None:
        return
    folder = s.collected_dir / "rejected" / reason
    folder.mkdir(parents=True, exist_ok=True)
    shutil.move(str(dest), str(folder / dest.name))


if __name__ == "__main__":
    main()
