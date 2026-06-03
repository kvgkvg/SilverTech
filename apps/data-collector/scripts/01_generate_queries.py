from __future__ import annotations

import json

from src.config import get_settings
from src.seeds import generate_queries, load_seeds


def main() -> None:
    s = get_settings()
    brands, devices = load_seeds(s.seeds_dir / "brands.json", s.seeds_dir / "device_types.json")
    queries = generate_queries(brands, devices)
    s.collected_dir.mkdir(parents=True, exist_ok=True)
    out = s.collected_dir / "queries.jsonl"
    with out.open("w") as f:
        for q in queries:
            f.write(json.dumps(q.to_dict()) + "\n")
    print(f"[01] wrote {len(queries)} queries -> {out}")


if __name__ == "__main__":
    main()
