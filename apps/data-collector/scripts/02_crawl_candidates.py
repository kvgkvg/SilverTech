from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from src.config import get_settings
from src.crawl.image_search import polite_sleep, search_query
from src.models import Candidate


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1000, help="max candidates total")
    args = parser.parse_args()

    s = get_settings()
    queries_path = s.collected_dir / "queries.jsonl"
    queries = [json.loads(line) for line in queries_path.read_text().splitlines() if line.strip()]

    out = s.collected_dir / "candidates.jsonl"
    s.collected_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    with out.open("w") as f:
        for q in queries:
            if count >= args.limit:
                break
            hits = search_query(q["query"], s.user_agent, s.results_per_query)
            for hit in hits:
                if count >= args.limit:
                    break
                count += 1
                cand = Candidate(
                    candidate_id=f"cand_{count:06d}",
                    query=q["query"],
                    brand_hint=q["brand"],
                    device_type_hint=q["device_type"],
                    source_url=hit["source_url"],
                    image_url=hit["image_url"],
                    alt_text=hit["alt_text"],
                    page_title=hit["page_title"],
                    created_at=_now(),
                )
                f.write(json.dumps(cand.to_dict()) + "\n")
            print(f"[02] query={q['query']!r} hits={len(hits)} total={count}")
            polite_sleep(s.crawl_delay_seconds)
    print(f"[02] wrote {count} candidates -> {out}")


if __name__ == "__main__":
    main()
