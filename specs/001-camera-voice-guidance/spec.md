# Feature Specification: SilverTech Camera Voice Guidance

**Feature Branch**: `001-camera-voice-guidance`

**Created**: 2026-06-02

**Status**: Draft

**Input**: User description: "Create the baseline specification for SilverTech, a mobile application that helps elderly users operate household electronic appliances by using the phone camera, Vietnamese voice input, logo-guided template matching, and visual AR guidance. The MVP focuses on washing machine/control panel use cases first and must not require QR stickers."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get Guided Help From Camera and Voice (Priority: P1)

An elderly user opens SilverTech, points the phone at an appliance control
panel, asks a Vietnamese question, and receives one clear instruction at a time
with the correct button highlighted on the live camera view.

**Why this priority**: This is the core value of the MVP: helping an elderly
user complete a household appliance task without help from family members.

**Independent Test**: Give the user a supported washing machine panel and a
Vietnamese task such as "Làm sao để giặt nhanh?". The user succeeds when they
can follow the displayed steps and identify the correct highlighted controls
without outside assistance.

**Acceptance Scenarios**:

1. **Given** a supported appliance panel is visible and the template match is
   confident, **When** the user asks a Vietnamese voice question, **Then** the
   app shows a large-text Vietnamese instruction and highlights the correct
   button for the current step.
2. **Given** a multi-step task is generated, **When** the user taps the next
   step control, **Then** the app advances to the next instruction and updates
   the highlighted button.
3. **Given** the user asks where a specific button is, **When** that button
   exists in the matched template, **Then** the app highlights that button and
   provides a short Vietnamese explanation.

---

### User Story 2 - Recover Safely When Recognition Is Uncertain (Priority: P2)

An elderly user scans a panel under poor conditions or with an unsupported
layout. Instead of guessing, SilverTech explains the problem in simple
Vietnamese and asks the user to rescan, move closer, reduce glare, scan a wider
area, or select the device manually.

**Why this priority**: Wrong button guidance is a critical failure. Safe
uncertainty handling is required before the app can be trusted.

**Independent Test**: Present the app with blurred, glared, partial, low-light,
or unsupported panel views. The test passes when the app refuses to highlight
uncertain buttons and provides a clear recovery action.

**Acceptance Scenarios**:

1. **Given** localization confidence is below the accepted threshold, **When**
   the user asks for guidance, **Then** the app does not highlight any button and
   asks the user to rescan or adjust the camera.
2. **Given** the logo is not visible, **When** the app cannot narrow candidate
   templates, **Then** it asks the user to scan a wider area or manually select
   the brand.
3. **Given** speech recognition fails, **When** the user still needs help,
   **Then** the app offers typed Vietnamese input.

---

### User Story 3 - Maintain a Reviewed Template Library (Priority: P3)

A maintainer or reviewer adds and reviews appliance control-panel templates so
SilverTech can expand coverage while keeping official button guidance
trustworthy.

**Why this priority**: Button highlights are only safe when they come from a
reviewed template with known button positions and button IDs.

**Independent Test**: Submit a new template image with labeled buttons, review
it, and verify that it is not used for official guidance until accepted.

**Acceptance Scenarios**:

1. **Given** a submitted template is unreviewed, **When** a user scans a matching
   appliance, **Then** the app does not treat that submission as an official
   guidance source.
2. **Given** a reviewer accepts a submitted template, **When** the template is
   published as official, **Then** future guidance can reference its validated
   button IDs and button regions.
3. **Given** multiple templates exist for the same brand, **When** a user scans
   a panel, **Then** the system distinguishes the matching layout rather than
   assuming one brand has one button arrangement.

### Edge Cases

- The camera view is blurred, glared, too dark, partially cropped, or moving.
- The logo or brand is not visible near the panel.
- The detected brand has several candidate templates with similar layouts.
- The appliance panel is unsupported or only partly represented in the template
  database.
- The matched template becomes unreliable after the user moves the phone.
- The user's Vietnamese voice query is noisy, incomplete, or not recognized.
- The generated guidance cannot map the user's intent to valid buttons in the
  matched template.
- The generated guidance references an invalid button ID.
- A crowdsource submission includes people, private scenes, or non-panel
  imagery.
- A user needs a manual brand or template selection path without navigating a
  complex menu.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The app MUST open directly into a camera scanning screen with a
  simple Vietnamese instruction telling the user to point the camera at the
  appliance control panel.
- **FR-002**: The app MUST attempt to identify the appliance brand or logo from
  the control panel or nearby front panel area when visible.
- **FR-003**: The system MUST use the detected brand or manual brand selection
  to retrieve candidate templates, while allowing multiple templates per brand.
- **FR-004**: The system MUST distinguish templates by matching the live panel
  view against stored template images rather than assuming that a brand maps to
  a single layout.
- **FR-005**: The system MUST align the selected template to the camera view and
  project stored button regions into the live view before any button is
  highlighted, using a geometric alignment method that can verify the template
  and camera view are spatially consistent.
- **FR-006**: The system MUST calculate localization confidence using matching
  quality, matched-feature support, projected geometry quality, and geometric
  plausibility.
- **FR-007**: The app MUST require rescanning, camera adjustment, or manual
  confirmation when confidence is below the accepted threshold.
- **FR-008**: The app MUST NOT require QR stickers or QR anchors for normal
  device recognition or button localization.
- **FR-009**: The template database MUST store brand, model or template ID,
  appliance type, template image, optional logo region, panel region, button
  bounding boxes, button IDs, button labels, button functions, source status,
  review status, and version.
- **FR-010**: The system MUST keep official templates separate from unreviewed
  crowdsource submissions.
- **FR-011**: The app MUST accept Vietnamese voice input for appliance-help
  questions.
- **FR-012**: The system MUST provide a typed Vietnamese input fallback when
  speech recognition fails or the user prefers typing.
- **FR-013**: The system MUST retrieve the matched template and available
  button list before generating user-facing steps.
- **FR-014**: Generated instructions MUST use only valid `button_id` values from
  the matched template.
- **FR-015**: The system MUST validate every generated `button_id` before the
  app displays or speaks a step.
- **FR-016**: If generated instructions reference invalid buttons, the system
  MUST reject the result and either regenerate the guidance or return a friendly
  Vietnamese error.
- **FR-017**: The app MUST display one guidance step at a time in large,
  high-contrast Vietnamese text.
- **FR-018**: The app MUST highlight the required button for the current step on
  the live camera view only after confidence and button-ID validation pass.
- **FR-019**: The app MUST allow the user to move to the next guidance step with
  a simple control.
- **FR-020**: The app SHOULD optionally read the current instruction aloud in
  Vietnamese.
- **FR-021**: The app MUST stop highlighting and ask for rescanning when tracking
  confidence drops.
- **FR-022**: The app MAY allow users or maintainers to submit new device
  templates by capturing panel images and labeling button positions.
- **FR-023**: Template review MUST support accepting, editing, or rejecting
  submitted templates before they become official.
- **FR-024**: The official template database MUST be versioned.
- **FR-025**: The MVP MUST support a small manually labeled template database
  covering at least 2-3 real household appliances, with washing machine panels
  prioritized.
- **FR-026**: The MVP MUST exclude production account management, payment,
  large-scale template marketplace features, complex social features, and full
  offline reasoning.
- **FR-027**: The UI MUST use minimal choices, large text, high contrast, and
  plain Vietnamese recovery instructions suitable for elderly users.
- **FR-028**: The system MUST log localization confidence, selected template,
  user query text, generated steps, and validation errors for debugging and
  evaluation while minimizing retained personal data.
- **FR-029**: Images used for template submission or debugging MUST be limited
  to appliance control panels and MUST avoid people or private scenes.

### Key Entities *(include if feature involves data)*

- **Device Template**: A reviewed or submitted appliance panel record containing
  brand, appliance type, model/template ID, template image, panel region,
  optional logo region, version, source status, review status, and associated
  button definitions.
- **Button Definition**: A labeled appliance control with a stable `button_id`,
  button label, function description, and bounding box within the template.
- **Template Match Result**: The selected template, candidate templates,
  confidence state, quality measurements, projected button regions, and
  recovery reason when matching is not confident.
- **User Query**: A Vietnamese text request derived from voice or typed input,
  associated with the current matched template and intended appliance task.
- **Guidance Step**: One user-facing Vietnamese instruction linked to a valid
  `button_id`, optional spoken text, and current-step display order.
- **Template Submission**: A proposed template image and button-labeling data
  that remains unofficial until a reviewer accepts, edits, or rejects it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 80% of elderly or elderly-like test users can complete a
  supported washing machine task using camera and Vietnamese guidance without
  outside assistance.
- **SC-002**: For supported templates under standard lighting, at least 90% of
  accepted matches place the visible button highlight within the intended button
  area during guided steps.
- **SC-003**: In low-confidence scans, unsupported layouts, or invalid guidance
  cases, the app avoids showing a wrong confident button highlight in 100% of
  validation tests.
- **SC-004**: At least 95% of generated guidance responses for supported tasks
  reference only valid `button_id` values from the matched template after
  validation.
- **SC-005**: Users see either a guidance step or a clear recovery instruction
  within 5 seconds of asking a question during standard MVP test conditions.
- **SC-006**: The MVP includes official, reviewed templates for at least 2-3
  real washing machine or household appliance panels before release testing.
- **SC-007**: At least 90% of usability-test participants can understand the
  next action from the displayed Vietnamese instruction without opening a menu.
- **SC-008**: 100% of submitted templates remain excluded from official runtime
  guidance until reviewed and accepted.

## Assumptions

- The MVP targets Android phones first, especially low-to-mid-range devices, and
  later platforms are outside the baseline specification.
- The first appliance category is washing machines; other supported appliances
  may be added only when reliable reviewed templates exist.
- Vietnamese is the primary language for voice input, displayed instructions,
  recovery prompts, and optional spoken guidance.
- Initial template coverage is manually curated and reviewed by the project
  team or designated maintainers.
- The app may need network access for speech recognition, instruction
  generation, template search, logging, or template review workflows.
- The MVP does not require user accounts for ordinary appliance guidance.
- Debug logs and evaluation records are retained only as long as needed to
  improve recognition, guidance quality, and template coverage.
