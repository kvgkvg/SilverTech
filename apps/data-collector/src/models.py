from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class QueryRecord:
    query: str
    brand: str
    device_type: str
    intent: str = "panel_image"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Candidate:
    candidate_id: str
    query: str
    brand_hint: str
    device_type_hint: str
    source_url: str
    image_url: str
    alt_text: str = ""
    page_title: str = ""
    license: str = "unknown"
    usage_note: str = "research/internal only unless license verified"
    created_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProcessedRecord:
    candidate_id: str
    query: str
    brand_hint: str
    device_type_hint: str
    source_url: str
    image_url: str
    alt_text: str = ""
    page_title: str = ""
    image_path: Optional[str] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    file_size: Optional[int] = None
    ocr_text: list[str] = field(default_factory=list)
    ocr_joined: str = ""
    brand: Optional[str] = None
    brand_source: Optional[str] = None
    has_visible_logo: bool = False
    phash: Optional[str] = None
    status: str = "candidate"
    reject_reason: Optional[str] = None
    license: str = "unknown"
    usage_note: str = "research/internal only unless license verified"
    created_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
