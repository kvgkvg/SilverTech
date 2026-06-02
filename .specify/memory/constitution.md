<!--
Sync Impact Report
Version change: template -> 1.0.0
Modified principles:
- Placeholder principle 1 -> I. Elderly-First UX
- Placeholder principle 2 -> II. Safety and Button Accuracy First
- Placeholder principle 3 -> III. Logo-Guided Template Matching
- Placeholder principle 4 -> IV. Template Database as Source of Truth
- Placeholder principle 5 -> V. Hybrid On-Device and Server Architecture
Added sections:
- Additional Product Constraints
- Development Workflow and Quality Gates
Removed sections:
- Placeholder section headings and example comments
Templates requiring updates:
- updated .specify/templates/plan-template.md
- updated .specify/templates/spec-template.md
- updated .specify/templates/tasks-template.md
- reviewed .specify/templates/commands/*.md (directory absent; no files to update)
- reviewed AGENTS.md (no principle-specific change required)
Follow-up TODOs: None
-->
# SilverTech Constitution

## Core Principles

### I. Elderly-First UX
SilverTech MUST be usable by elderly users with minimal technical knowledge.
Primary flows MUST be one-tap or step-by-step, with large text, high contrast,
clear touch targets, and plain-language labels. The MVP MUST avoid login,
complex menus, and unnecessary configuration unless a feature cannot work
without them. Every error state MUST provide a simple recovery instruction,
such as "move the camera closer", "scan the control panel again", or "select
device manually".

Rationale: The product succeeds only when users can complete appliance tasks
without needing technical confidence, memory-heavy navigation, or caregiver
intervention.

### II. Safety and Button Accuracy First
SilverTech MUST NOT confidently highlight a control-panel button when
localization confidence is low. When the system is uncertain, it MUST ask the
user to rescan or manually confirm before giving button guidance. Wrong button
guidance is a critical failure. Every highlighted button MUST come from a
verified device template or a reviewed and validated user submission.

Rationale: A wrong appliance action can damage clothing, food, devices, or user
trust. Uncertainty must be visible and recoverable rather than hidden.

### III. Logo-Guided Template Matching
SilverTech MUST NOT rely on QR codes as the primary spatial anchor. The core
localization method MUST be logo-guided template matching. Logo or brand
detection MAY narrow candidate templates, but button localization MUST align a
selected template to the live camera frame using ORB/SIFT image matching and
homography or affine transformation. Button positions MUST be projected from
pre-labeled template coordinates to the user's camera frame. Confidence checks
are mandatory before showing AR overlays.

Rationale: Household appliances do not reliably expose QR anchors, while
brand/logo and panel features are available in normal use and preserve a more
natural user flow.

### IV. Template Database as Source of Truth
Device templates MUST store brand, model or template ID, template image, logo
bounding box when available, panel metadata, button bounding boxes, button IDs,
labels, and usage descriptions. Runtime button guidance MUST reference
`button_id` values from the database. LLM responses MUST only use valid
`button_id` values returned by the backend for the matched device/template.
Crowdsource submissions MAY be accepted, but submitted templates MUST be
reviewed before becoming official guidance sources.

Rationale: A structured template database gives the system auditable button
coordinates, stable identifiers, and a controlled path for expanding coverage.

### V. Hybrid On-Device and Server Architecture
Camera processing, template matching, homography estimation, tracking, and AR
overlay SHOULD run on-device where feasible. STT, LLM reasoning, template
search, and data management MAY run on the server. Feature plans MUST justify
any server dependency that blocks guidance for low-to-mid-range mobile devices.

Rationale: Near-camera feedback must remain responsive, while server-side
services can handle heavier language, search, and management workflows.

## Additional Product Constraints

Performance and robustness requirements are mandatory acceptance concerns. The
app MUST provide near-real-time camera feedback appropriate for user guidance,
even when perfect automation is not possible. The system MUST handle blur,
glare, partial panel view, low light, and camera movement through confidence
checks and rescan prompts. Tracking MAY use optical flow after a confident
template match, but tracking MUST reset when confidence drops.

Privacy and data minimization are required by default. Images used for
crowdsource or template submission MUST be limited to appliance control panels
and MUST avoid people or private scenes. The system MUST store only data needed
for device recognition, debugging, and template improvement. Voice queries and
LLM logs SHOULD be minimized and used only for debugging or evaluation.

MVP scope MUST prioritize reliability over broad coverage. Initial releases
SHOULD focus on a small number of real devices and templates, preferably 2-3
appliance types, until button localization and guidance are dependable.
Nice-to-have features MUST be postponed when they threaten button-localization
reliability, elderly-first UX, privacy, or measurable acceptance.

## Development Workflow and Quality Gates

Every feature specification MUST define acceptance criteria before
implementation. Button localization features MUST define localization accuracy,
match confidence, reprojection error, and user task success metrics. STT/LLM
flows MUST be evaluated by whether returned steps reference valid `button_id`
values and solve the user's intent. UI features MUST include elderly or
elderly-like usability testing whenever possible, or document why such testing
was not possible for the iteration.

Plans MUST document on-device versus server responsibilities, low-to-mid-range
device constraints, template database schema impact, privacy/data retention
impact, and safety fallback behavior. Tasks MUST include work for confidence
checks, recovery instructions, valid `button_id` enforcement, measurable tests,
and documentation updates whenever those concerns apply.

All specs, plans, tasks, API schemas, database schemas, and test results MUST be
documented. Any change from an approved specification MUST update the
corresponding spec, plan, and tasks before implementation continues.

## Governance

This constitution supersedes conflicting product, technical, or process
guidance for SilverTech. Each specification, plan, task list, implementation
review, and release decision MUST verify compliance with the Core Principles,
Additional Product Constraints, and Development Workflow and Quality Gates.

Amendments MUST be documented in this file with a Sync Impact Report describing
version changes, modified principles, added or removed sections, affected
templates, and follow-up TODOs. Dependent templates and runtime guidance MUST be
updated in the same change when the amendment affects future work.

Versioning follows semantic versioning. MAJOR changes remove or redefine
principles in a backward-incompatible way. MINOR changes add principles,
sections, or materially expanded guidance. PATCH changes clarify wording,
correct errors, or make non-semantic refinements.

Compliance review is required before implementation begins, after design
artifacts are produced, and before release. Critical failures include wrong
button guidance, unverified official template data, invalid LLM `button_id`
references, privacy-invasive image capture, and elderly users being unable to
recover from errors with the provided instructions.

**Version**: 1.0.0 | **Ratified**: 2026-06-02 | **Last Amended**: 2026-06-02
