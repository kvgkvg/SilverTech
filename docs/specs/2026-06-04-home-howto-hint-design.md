# Home "How to use" hint redesign

Date: 2026-06-04
Status: Approved (layout B)

## Problem

Home screen shows 3 instruction steps as separate boxed rows (`StepSummaryRow`,
`apps/mobile/lib/main.dart`). Each row is a `blueTint` container, rounded 15px,
with a white circular number badge. That visual = button affordance. Elderly
users mistake the steps for tappable buttons, though they have no `onTap` and do
nothing.

## Goal

Merge the 3 steps into ONE light "how to use" hint block that reads as
descriptive info, not actions. Remove all button affordance.

## Design (layout B — vertical timeline)

Single card replacing the 3 `StepSummaryRow` widgets:

```
┌─────────────────────────────────┐
│ 3 bước đơn giản                  │
│                                  │
│  ①  Đưa thiết bị vào khung       │
│  │                               │
│  ②  Hỏi bằng giọng nói           │
│  │                               │
│  ③  Làm theo nút sáng            │
└─────────────────────────────────┘
```

### Rules

- ONE container, not three. Reads as a single info block.
- Header label "3 bước đơn giản" → signals description, not action.
- Vertical connecting line between number badges → shows sequence.
- No button affordance:
  - flat tinted background (e.g. `surface2` or very light `blueTint`), NO
    drop shadow.
  - NO `InkWell` / `GestureDetector` / `onTap`.
  - number badges small + inline with text (not large standalone chips).
- Each step on its own line → large text stays readable for elderly users.

### Labels (unchanged)

1. Đưa thiết bị vào khung
2. Hỏi bằng giọng nói
3. Làm theo nút sáng

## Scope

- New widget `HowToHintCard` in `apps/mobile/lib/main.dart`.
- `HomeScreen.build`: replace the `...steps.indexed.map(StepSummaryRow)` block
  with one `HowToHintCard`.
- Remove `StepSummaryRow` if no other references.
- Keep `BigStartButton` and recent-devices section unchanged.

## Out of scope

- Camera/voice/guide screens.
- Step content/wording changes.
- Onboarding flow changes.

## Verification

- `dart analyze` clean on `apps/mobile/lib/main.dart` (if Dart available).
- Visual: home shows single flat hint block, no rows that look tappable.
