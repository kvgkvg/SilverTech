from __future__ import annotations

import json
from pathlib import Path

from src.models import QueryRecord


def generate_queries(brands: list[str], device_entries: list[dict]) -> list[QueryRecord]:
    records: list[QueryRecord] = []
    for brand in brands:
        for entry in device_entries:
            device_type = entry["device_type"]
            for device_query in entry["queries"]:
                records.append(
                    QueryRecord(
                        query=f"{brand} {device_query}",
                        brand=brand,
                        device_type=device_type,
                    )
                )
    return records


def load_seeds(brands_path: Path, devices_path: Path) -> tuple[list[str], list[dict]]:
    brands = json.loads(brands_path.read_text())
    devices = json.loads(devices_path.read_text())
    return brands, devices
