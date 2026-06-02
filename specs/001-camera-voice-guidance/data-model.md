# Data Model: SilverTech Camera Voice Guidance

## Entity: Device

Represents an appliance family or model line.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID/string | Yes | Primary identifier |
| brand | string | Yes | Normalized brand name, e.g. Toshiba |
| appliance_type | string | Yes | washing_machine, air_conditioner, tv, microwave, air_fryer |
| model_name | string | No | Specific model when known |
| display_name | string | Yes | Elderly-friendly display label |
| status | enum | Yes | active, archived |
| created_at | datetime | Yes | Creation timestamp |
| updated_at | datetime | Yes | Last update timestamp |

Relationships: One device has many templates.

Validation rules:
- `brand`, `appliance_type`, and `display_name` cannot be blank.
- `status=archived` devices cannot be selected for new official guidance.

## Entity: Template

Represents one reviewed or submitted control-panel layout.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID/string | Yes | Primary identifier |
| device_id | UUID/string | Yes | References Device |
| template_code | string | Yes | Stable code for this layout |
| template_image_url | string | Yes | URL or local path to panel image |
| logo_bbox | JSON | No | x, y, width, height in template coordinates |
| panel_bbox | JSON | No | x, y, width, height in template coordinates |
| feature_descriptor_path | string | No | Precomputed descriptor file path |
| version | integer | Yes | Increments when official template changes |
| status | enum | Yes | official, submitted, archived |
| created_at | datetime | Yes | Creation timestamp |
| updated_at | datetime | Yes | Last update timestamp |

Relationships: One template has many buttons, vision logs, LLM logs, and may
originate from a template submission.

Validation rules:
- Runtime guidance can use only `status=official` templates.
- Template image must show an appliance control panel, not people/private scenes.
- `template_code` must be unique per device/version.

State transitions:
- submitted -> official after reviewer acceptance.
- submitted -> archived after rejection or replacement.
- official -> archived when deprecated.

## Entity: Button

Represents one labeled appliance control in template coordinates.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID/string | Yes | Primary identifier |
| template_id | UUID/string | Yes | References Template |
| button_id | string | Yes | Stable runtime identifier |
| label | string | Yes | Label visible on panel when available |
| vietnamese_name | string | Yes | Elderly-friendly Vietnamese name |
| function_description | string | Yes | What the button does |
| bbox_template_coordinates | JSON | Yes | x, y, width, height |
| polygon_template_coordinates | JSON | No | More precise polygon |
| button_type | enum | Yes | physical, touch, dial, display, unknown |
| created_at | datetime | Yes | Creation timestamp |
| updated_at | datetime | Yes | Last update timestamp |

Relationships: Guidance steps reference buttons by `button_id` within one
template.

Validation rules:
- `(template_id, button_id)` must be unique.
- Runtime instructions cannot reference free-form button names without a valid
  `button_id`.
- Bounding boxes must lie inside the template image bounds.

## Entity: Submission

Represents a proposed new template from a user or maintainer.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID/string | Yes | Primary identifier |
| submitted_by | string | No | Nullable for MVP/no-account submissions |
| brand | string | Yes | Submitted brand |
| appliance_type | string | Yes | Submitted appliance type |
| image_url | string | Yes | Submitted panel image |
| proposed_labels_json | JSON | Yes | Proposed button labels/positions |
| status | enum | Yes | pending, accepted, rejected |
| reviewer_note | string | No | Reason or edit note |
| created_at | datetime | Yes | Creation timestamp |

Validation rules:
- Submissions cannot become official until reviewed.
- Submitted image must be limited to appliance control panel content.

State transitions:
- pending -> accepted after review creates/updates official template/buttons.
- pending -> rejected with reviewer note.

## Entity: LLM Log

Records guidance generation and validation for debugging/evaluation.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID/string | Yes | Primary identifier |
| template_id | UUID/string | Yes | Matched template |
| user_query | string | Yes | Minimized query text |
| stt_text | string | No | STT result when voice was used |
| prompt_summary | string | Yes | Summary, not full sensitive prompt where possible |
| raw_response | JSON/string | No | Raw response retained only for debugging |
| validated_steps_json | JSON | No | Accepted steps |
| validation_status | enum | Yes | accepted, regenerated, rejected, error |
| latency_ms | integer | Yes | End-to-end generation latency |
| created_at | datetime | Yes | Creation timestamp |

Validation rules:
- Accepted logs must contain only valid `button_id` values for the template.
- Retention should be minimized and configurable.

## Entity: Vision Log

Records matching confidence and failure reasons.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID/string | Yes | Primary identifier |
| template_id | UUID/string | No | Nullable when no template accepted |
| brand_candidate | string | No | Detected or selected brand |
| match_score | number | No | Composite matching score |
| inlier_count | integer | No | RANSAC inliers |
| inlier_ratio | number | No | Inliers / good matches |
| reprojection_error | number | No | Average reprojection error |
| accepted | boolean | Yes | Whether overlay may proceed |
| failure_reason | string | No | low_confidence, no_logo, glare, partial_view, unsupported |
| created_at | datetime | Yes | Creation timestamp |

Validation rules:
- `accepted=false` requires `failure_reason`.
- `accepted=true` requires template ID and confidence metrics.

## Value Object: LLM Guidance Output

```json
{
  "intent": "string",
  "steps": [
    {
      "step_number": 1,
      "instruction_vi": "string",
      "button_id": "string",
      "expected_result": "string"
    }
  ],
  "safety_note": "string|null"
}
```

Validation rules:
- `steps` must be non-empty for successful guidance.
- Every `button_id` must exist for the selected template.
- Step numbers must be sequential.
- Invalid output is rejected, regenerated, or converted to a friendly error.
