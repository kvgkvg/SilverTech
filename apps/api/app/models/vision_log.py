from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VisionLog:
    id: str
    template_id: str | None
    brand_candidate: str | None
    match_score: float | None
    inlier_count: int | None
    inlier_ratio: float | None
    reprojection_error: float | None
    accepted: bool
    failure_reason: str | None
    created_at: str
