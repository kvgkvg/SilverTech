from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class Point(BaseModel):
    x: float
    y: float


class ButtonSchema(BaseModel):
    button_id: str
    label: str
    vietnamese_name: str
    function_description: str
    bbox_template_coordinates: BBox
    polygon_template_coordinates: list[Point] | None = None
    button_type: str


class TemplateSummary(BaseModel):
    id: str
    brand: str
    appliance_type: str
    template_code: str
    version: int
    status: str = "official"
    template_image_url: str
    logo_bbox: BBox | None = None
    panel_bbox: BBox | None = None
    feature_descriptor_url: str | None = None


class LogoOffset(BaseModel):
    """Button placement relative to the logo anchor, in logo-width units."""

    dx: float
    dy: float
    dw: float
    dh: float


class TemplateDetail(TemplateSummary):
    buttons: list[ButtonSchema]
    logo_offsets: dict[str, LogoOffset] = Field(default_factory=dict)


class VisionCandidateRequest(BaseModel):
    brand: str | None = None
    appliance_type: str | None = None
    brand_confidence: float | None = None


class VisionCandidateResponse(BaseModel):
    candidates: list[TemplateSummary]


class STTResponse(BaseModel):
    text: str
    confidence: float


class QueryRequest(BaseModel):
    template_id: str
    user_query_text: str
    stt_metadata: dict[str, Any] | None = None


class GuidanceStep(BaseModel):
    step_number: int = Field(ge=1)
    instruction_vi: str
    button_id: str
    expected_result: str


class GuidanceOutput(BaseModel):
    intent: str
    steps: list[GuidanceStep] = Field(min_length=1)
    safety_note: str | None = None


class VisionLogRequest(BaseModel):
    template_id: str | None = None
    brand_candidate: str | None = None
    match_score: float | None = None
    inlier_count: int | None = None
    inlier_ratio: float | None = None
    reprojection_error: float | None = None
    accepted: bool
    failure_reason: str | None = None


class SubmissionCreate(BaseModel):
    submitted_by: str | None = None
    brand: str
    appliance_type: str
    image_url: str
    proposed_labels_json: dict[str, Any]


class SubmissionReview(BaseModel):
    decision: str = Field(pattern="^(accept|edit|reject)$")
    reviewer_note: str | None = None
    edited_template: dict[str, Any] | None = None
