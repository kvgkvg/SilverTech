# Feature Specification: SilverTech Prototype UI

**Feature Branch**: `002-prototype-ui`

**Created**: 2026-06-02

**Status**: Draft

**Input**: User description: "Fetch this design file, read its readme, and implement the relevant aspects of the design. Implement: SILVERTECH Prototype.html."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start Guided Help From Home (Priority: P1)

An elderly Vietnamese user opens SilverTech, sees a friendly home screen, and can start camera-based appliance guidance with one prominent action.

**Why this priority**: The design succeeds only if the main help flow is obvious and does not require technical confidence or menu hunting.

**Independent Test**: Open the app from a fresh state and verify that the user can identify SilverTech, understand the three-step guidance promise, and enter camera recognition from the primary button.

**Acceptance Scenarios**:

1. **Given** the app has just opened, **When** the user views the home screen, **Then** the screen shows the SilverTech brand, a greeting, a short Vietnamese prompt, a large "Bắt đầu hướng dẫn" action, and the three simple steps "Đưa thiết bị vào khung", "Hỏi bằng giọng nói", and "Làm theo nút sáng".
2. **Given** the user is on the home screen, **When** they choose the primary guidance action, **Then** the app moves to device recognition without requiring account setup or configuration.
3. **Given** the user has saved devices, **When** they view the home screen, **Then** recent devices are shown with clear names, models, last-used information, and a simple way to open guidance for a device.

---

### User Story 2 - Follow Camera, Voice, and Step Guidance Flow (Priority: P1)

An elderly user can move through recognition, voice question, and step-by-step guidance screens using large Vietnamese labels, clear status feedback, and highlighted controls.

**Why this priority**: This is the core prototype flow captured in the design handoff and is the most important path to validate with users.

**Independent Test**: Starting from the home screen, run the complete flow through recognition, accepted detection, voice input, and three guidance steps; verify that each screen displays the expected Vietnamese copy and one clear next action.

**Acceptance Scenarios**:

1. **Given** the user starts guidance, **When** recognition is active, **Then** the screen shows a dark camera preview area, a green recognition frame, direct-recognition status, and detected appliance/button counts.
2. **Given** recognition has a usable result, **When** the user accepts it, **Then** the app opens a dark voice-control view with the current device name, detected button count, a large microphone action, and an example Vietnamese question.
3. **Given** the user finishes voice input, **When** guidance begins, **Then** the app displays one step at a time with current-step progress, a highlighted target button when appropriate, repeat/back/next controls, and a completion state.

---

### User Story 3 - Add and Manage Devices (Priority: P2)

An elderly user or caregiver can add a device through a simple four-step wizard and then see it in the saved-device list.

**Why this priority**: Saved devices support repeat use while preserving the product's template-source-of-truth direction.

**Independent Test**: Start the add-device flow, complete photo, recognition, label review, and confirmation steps, save the device, and verify that the saved device appears in the device list with confirmation feedback.

**Acceptance Scenarios**:

1. **Given** the user starts adding a device, **When** the wizard opens, **Then** it shows four clearly labeled steps: "Chụp ảnh", "Nhận diện", "Gắn nhãn", and "Xác nhận".
2. **Given** the user completes the wizard, **When** they save the device, **Then** the app returns to the device list and displays a short confirmation message.
3. **Given** saved devices exist, **When** the user opens the device list, **Then** each device shows a name, model, last-used status, appliance icon, and an easy open action.

---

### User Story 4 - Adjust Accessibility Preferences (Priority: P3)

An elderly user or caregiver can open settings and adjust readability and spoken-guidance preferences.

**Why this priority**: The prototype includes accessibility-oriented settings that support elderly-first use but are not required to complete the main guidance flow.

**Independent Test**: Open settings from the home screen and verify that font-size, read-aloud, and high-contrast controls are visible, large, and saveable.

**Acceptance Scenarios**:

1. **Given** the user opens settings, **When** preferences are displayed, **Then** the app shows controls for text size, reading instructions aloud, and high contrast using plain Vietnamese labels.
2. **Given** the user changes a preference, **When** they save, **Then** the app returns to the previous screen without disrupting the guidance flow.

### Edge Cases

- Recognition flow is entered before a real camera feed is available; the screen still provides a safe simulated preview and clear next action for demo use.
- Text with Vietnamese diacritics must remain readable and must not clip or overlap in large buttons, cards, or bottom guidance controls.
- Back navigation from pushed screens returns to the previous safe screen without losing the root home/device tabs.
- Add-device wizard cannot proceed from the photo step until a photo state is present.
- Guidance controls must not show a confident target highlight on the final "done" step.
- Confirmation messages must not cover primary navigation or required action buttons.
- Small phone screens must preserve large touch targets and avoid horizontal overflow.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The app MUST present a polished SilverTech home screen matching the design handoff's elderly-first Vietnamese flow, including greeting, primary camera guidance action, simple three-step explanation, recent devices, settings access, and add-device access.
- **FR-002**: Users MUST be able to navigate from home to recognition, voice input, guidance, add-device wizard, device list, and settings through visible controls shown in the prototype.
- **FR-003**: The recognition screen MUST show an appliance-control preview, green scan framing, live-recognition status, detected device count, detected button count, retry action, and accept-result action.
- **FR-004**: The voice screen MUST show the recognized device name, detected button count, appliance-control preview, large microphone action, listening state, and an example Vietnamese question.
- **FR-005**: The guidance screen MUST show one instruction step at a time, visual step progress, the relevant target button highlight before completion, a completion state, and large controls for repeat, previous, next, restart, and finish.
- **FR-006**: The add-device flow MUST present four ordered steps for photo capture, recognition, label review, and confirmation with clear status and navigation controls.
- **FR-007**: Users MUST be able to edit recognized button labels in the label-review step before saving.
- **FR-008**: Saving a device from the wizard MUST add it to the saved-device list and show a confirmation message.
- **FR-009**: The device list MUST show all saved devices with appliance type, model, last-used status, and a direct open action.
- **FR-010**: Settings MUST expose text-size, read-aloud, and high-contrast controls with large labels and save action.
- **FR-011**: User-facing text in prototype-derived screens MUST use Vietnamese copy from the design handoff unless an existing product-safety requirement requires clearer wording.
- **FR-012**: Touch targets for primary actions, tab items, icon buttons, wizard controls, and guidance controls MUST be large enough for elderly users.
- **FR-013**: UI colors, typography feel, spacing, cards, rounded controls, dark camera surfaces, blue primary actions, green success/highlight states, orange warning states, and red detected-button labels MUST remain visually consistent with the design handoff.
- **FR-014**: The app MUST preserve existing safety behavior that only real guidance highlights may be driven by valid confidence and button identifiers when connected to runtime data.
- **FR-015**: The prototype UI MUST remain demonstrable without requiring production speech, camera, or template services to be active.

### Key Entities *(include if feature involves data)*

- **Demo Device**: A saved or recognized appliance shown in the UI with id, appliance type, visual tone, name, short model, full model, and last-used label.
- **Prototype Guidance Step**: A user-facing guidance instruction with step type, target button, title, hint, order, and completion state.
- **Button Label Draft**: An editable label for a recognized control-panel button during the add-device wizard.
- **Accessibility Preference**: A user-visible setting for text size, spoken guidance, or high contrast.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A tester can complete the home-to-recognition-to-voice-to-guidance path in under 2 minutes without reading external instructions.
- **SC-002**: 100% of primary screens from the design handoff are represented in the app: home, recognition, voice control, step guidance, add-device wizard, device list, and settings.
- **SC-003**: 100% of visible prototype-derived Vietnamese labels used in primary actions and screen titles render with correct diacritics.
- **SC-004**: At least 95% of interactive controls in prototype-derived screens meet or exceed a 56 px touch target or equivalent comfortable mobile tap area.
- **SC-005**: No primary action text clips, overlaps, or becomes unreadable on the default demo viewport and a small mobile viewport.
- **SC-006**: The add-device demo flow saves a new device and shows it in the device list in 100% of widget-test runs.
- **SC-007**: The implementation preserves existing controller-level safety tests for camera highlights and guidance state.

## Assumptions

- The implementation target is the existing SilverTech mobile app in this repository.
- The design handoff is an interactive prototype, so the mobile app may use simulated appliance preview and demo state where real camera, voice, or template services are not yet wired.
- The prototype's phone frame is a handoff presentation device; production mobile screens should fill the app viewport rather than rendering a desktop phone frame inside the app.
- Vietnamese is the primary visible language for prototype-derived UI.
- The design's friendly rounded typography can be approximated by the closest available app font unless a specific font asset is later added.
- Existing backend, vision, and guidance safety contracts remain authoritative for real runtime behavior.
