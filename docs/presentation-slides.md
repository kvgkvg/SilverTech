# SilverTech — Presentation Slide Content (15 slides)

Diagram-first, minimal on-slide text. Each slide lists: **On slide** (what the audience
sees), **Diagram** (what to draw), and **Speaker notes** (what to say). No code, file
names, or implementation details appear on the slides themselves.

---

## Slide 1 — Title

**On slide**
- **SilverTech**
- *Point your camera. Ask in Vietnamese. Get guided, button by button.*
- An elderly-first mobile assistant for household appliance control panels

**Diagram**
- App logo / hero mockup: phone pointed at a washing machine panel, one button
  highlighted in green, a speech bubble with a Vietnamese question.

**Speaker notes**
- One sentence pitch: elderly users struggle with modern appliance panels; SilverTech
  looks at the panel through the camera, listens to a spoken question, and highlights
  exactly which button to press, step by step, in Vietnamese.

---

## Slide 2 — Problem & Solution Flow

**On slide**
- Pain points (icons, one word each):
  - **Small labels** — dense panels, tiny icons, foreign-language text
  - **Too many modes** — dozens of combinations, unclear order of presses
  - **Fear of breaking it** — wrong press feels risky, so the appliance goes unused
  - **Manuals don't help** — long, technical, often lost
- Solution flow (single horizontal arrow strip):
  **📷 Point camera → 🗣 Ask in Vietnamese → ✅ Step-by-step, each step points at one real button**

**Diagram**
- Left half: 3–4 pain-point icons with single-word captions.
- Right half: 3-stage arrow flow ending on a phone screen with a highlighted button.

**Speaker notes**
- The key differentiator: guidance is not generic text — every step is anchored to a
  physical button that the app has located on the live camera image, so the user is
  never told to press something that isn't there.

---

## Slide 3 — Architecture: Three Layers

**On slide**
- **Mobile app** — camera, voice in/out, big-font elderly-first UI
- **Backend server** — template library, guidance brain, safety validation, review workflow
- **Computer vision** — brand logo detection, template matching, button projection

**Diagram**
- Three stacked boxes with arrows:
  - Mobile app ⇄ Backend (camera frames up, guidance + button positions down)
  - Backend ⇄ Vision (frame in, matched device + button geometry out)
- Side annotation: voice recognition stays **on the phone**; the AI "brain" and the
  device database live on the **server**.

**Speaker notes**
- Responsibility split: the phone owns everything real-time and personal (camera
  preview, speech, accessibility); the server owns everything shared and validated
  (the reviewed device library, guidance generation, safety checks); the vision layer
  is the specialist that turns a raw photo into "this exact device, buttons here."

---

## Slide 4 — Data Flow: 7 Steps from Camera to Spoken Guidance

**On slide** (numbered ring or vertical pipeline, one short label each)
1. **Capture** — camera frame of the appliance panel
2. **Recognize** — vision layer finds the brand logo, then the exact device model
3. **Project** — known button locations are mapped onto the user's own image
4. **Ask** — user speaks (or types) a question in Vietnamese
5. **Generate** — AI layer turns question + button database into steps
6. **Validate** — every step is checked against the real buttons before it is shown
7. **Guide** — steps shown one at a time, active button highlighted, read aloud

**Diagram**
- Circular or vertical 7-node pipeline; color the validation node differently (it is a
  gate, not a transformation).

**Speaker notes**
- Emphasize step 6: the system never trusts the AI output blindly — a dedicated gate
  rejects any step referring to a button that does not exist on the matched device.

---

## Slide 5 — Device Recognition (No Deep Learning)

**On slide**
- **Brand first, model second** — classical image matching, zero training
- Stage 1: compare the frame against a gallery of **brand logos** → "this is a Panasonic"
- Stage 2: among that brand's devices, match distinctive **visual features** of each
  panel → "this exact microwave model"
- Stage 3: compute the geometric transform between the stored panel photo and the
  live frame

**Diagram**
- Funnel: camera frame → [logo gallery: Panasonic / Toshiba / Electrolux / Daikin…] →
  brand's template shelf → one winning template → transform arrow onto the live frame.

**Speaker notes**
- Why classical matching instead of a neural network: no dataset to collect, no
  training or GPU needed, a new device is supported the moment one labeled photo
  exists, and every decision is explainable (match counts, geometry) — important for
  a safety-minded product and realistic for a small team.
- The brand logo acts as an anchor: it is the most distinctive, most repeatable
  element on any panel, so finding it first cuts the search space and stabilizes the
  geometry.

---

## Slide 6 — Confidence Scoring: When Do We Trust a Match?

**On slide**
- A match must pass **all three gates**:
  - **Enough evidence** — a minimum number of agreeing feature matches
  - **Enough agreement** — at least half of the candidate matches must be consistent
  - **Tight geometry** — projected points may deviate only a few pixels
- Plus anti-fooling checks: the winning brand must clearly beat the runner-up, and
  degenerate geometry (everything collapsing to one point) is rejected
- Result is one of **three tiers**:
  - ✅ **Refined** — full geometric match; buttons placed precisely
  - 🟡 **Coarse** — logo found but geometry weak; approximate placement only
  - ❌ **Rejected** — not confident; ask the user to rescan

**Diagram**
- Three-gate turnstile leading to a traffic light (green / yellow / red tier).

**Speaker notes**
- Design principle: a wrong "confident" answer is worse than an honest "I'm not sure."
  Every rejection path leads to a friendly retry, never to a guess.
- The margin rule (winner must clearly beat second place) exists because unrelated
  text on a panel can accidentally resemble a logo; requiring a decisive winner and a
  sane geometric fit filters those false positives.

---

## Slide 7 — Button Positioning & Tracking

**On slide**
- Button locations are labeled **once** on a reference photo of each device
- At runtime, the geometric transform from recognition **projects** those boxes onto
  the user's own image — the overlay follows perspective and scale
- The display crops to just the **panel region** (buttons + logo) so elderly eyes see
  a large, uncluttered view
- Motion safety: if the frame becomes unstable, confidence drops and the highlight is
  **removed** rather than shown in the wrong place; the user is asked to rescan

**Diagram**
- Left: reference photo with labeled rectangles. Middle: arrow labeled "geometric
  transform." Right: user's skewed photo with the same rectangles correctly warped;
  active button green, others outlined.
- Small inset: shaky phone icon → highlight disappears → "hold steady / rescan" prompt.

**Speaker notes**
- One labeling effort serves every future user of that device model.
- The tracking rule is deliberately conservative: a highlight on the wrong button is a
  safety failure, so any doubt hides the highlight and triggers re-recognition.

---

## Slide 8 — Voice: On-Device Recognition, Platform-Adaptive

**On slide**
- **Speech-to-text runs on the phone** — a compact Vietnamese model, fully offline
  - Private: audio never leaves the device
  - Reliable: works with weak or no internet
  - Fast: no round trip to a cloud service
- **Platform-adaptive**: on the web demo (where the on-device engine cannot run) the
  app transparently switches to the browser's built-in speech recognition
- **Text-to-speech** reads every step aloud — Vietnamese voice, deliberately **slow
  rate** tuned for elderly listeners; typing is always available as a fallback

**Diagram**
- Phone with microphone → on-device model chip → text; a small fork showing
  "web build → browser speech engine." Speaker icon with a turtle ("slow, clear").

**Speaker notes**
- The offline choice is elderly-first thinking: target users often have unreliable
  connectivity and heightened privacy concerns; a 30-million-parameter compact model
  is enough for short appliance questions.
- The same abstraction lets the team swap recognition engines per platform without
  touching the rest of the app.

---

## Slide 9 — AI Layer: A Swappable Brain

**On slide**
- Guidance generation sits behind a **provider switch**:
  - **Test mode** — a deterministic keyword matcher; free, instant, predictable —
    used for development and automated tests
  - **Real mode** — a large language model, given the user's question **plus the
    matched device's full button database**, must answer in a strict structured format
- Same contract either way: *intent + numbered steps (each tied to one button) +
  optional safety note*

**Diagram**
- A socket/plug metaphor: the app plugs into either "Mock" or "LLM" cartridge; both
  output the same structured guidance shape.

**Speaker notes**
- The LLM never answers from general knowledge alone — it is handed the exact list of
  buttons on the recognized device, with Vietnamese names and function descriptions,
  and is told to use only those.
- Because both providers speak the same contract, the entire pipeline (validation, UI,
  logging) is testable without any AI cost or nondeterminism.

---

## Slide 10 — Safety & Validation: Never Trust, Always Verify

**On slide**
- Every AI answer passes a **hard gate** before the user sees it:
  - ✅ Each step's button must **exist on the matched device** — otherwise the whole
    answer is rejected
  - ✅ The answer must fit the **strict structured format** — malformed output is rejected
  - ✅ **Off-topic questions are refused** — "what's the weather?" gets a polite
    Vietnamese refusal, never a random button suggestion
- Every attempt — accepted or rejected — is **logged** with latency for audit

**Diagram**
- Conveyor belt: AI answer → three stamp stations (real buttons? valid format?
  on-topic?) → either "user screen" or "rejected + logged."

**Speaker notes**
- This is the core correctness invariant of the whole product: guidance must never
  reference a button that doesn't exist. A hallucinated button on a stove or washer is
  a genuine safety issue for an elderly user.
- The refusal path matters just as much: the earlier behavior of "if unsure, suggest
  the first button" was replaced by an explicit out-of-scope refusal on both the test
  and real AI paths.

---

## Slide 11 — Growing the Library: Human-in-the-Loop, No Retraining

**On slide**
- Anyone can add a new appliance **inside the app**, in four steps:
  1. Photograph the panel
  2. Enter brand / type / model (auto-fills naming and codes)
  3. Draw boxes: the logo, then each button — with a name and what it does
  4. Submit
- Submission goes to an **admin review queue** → accept / edit / reject
- An accepted submission **immediately** becomes a recognizable device — because
  recognition is matching, not learning, **no model is ever retrained**

**Diagram**
- Loop: user labels on phone → review desk (human checkmark) → device library →
  recognition for all users → (arrow back) more users, more devices.

**Speaker notes**
- This is the payoff of the classical-matching decision on slide 5: the cost of
  supporting a new device is one photo and a few minutes of labeling, gated by a human
  reviewer for quality — not a data-collection and retraining cycle.

---

## Slide 12 — Testing Across All Three Layers

**On slide**
- **Backend** — end-to-end API tests + contract tests against the published API
  specification: guidance flow, invalid-button rejection, off-topic refusal,
  submission review states, startup and schema integrity
- **Vision** — deterministic synthetic-geometry tests: confidence gates, transform
  estimation, and button projection verified against known-answer fixtures (stable —
  no flaky real photos in CI)
- **Mobile** — logic tests for button projection math, step-by-step player, and
  rescan behavior; widget tests walk the full user journey (home → recognize → ask →
  guided steps) against fake services

**Diagram**
- The three architecture boxes from slide 3, each with a test-tube icon and its
  test-focus keyword (contracts / geometry / user journey).

**Speaker notes**
- The mock AI provider (slide 9) is what makes the backend suite deterministic; the
  synthetic fixtures do the same for vision. Real-photo validation is done manually
  with a dedicated debugging tool.

---

## Slide 13 — Fallback UX: Designed for the Worst Moment

**On slide** (staircase, best case at top)
1. **Ideal** — device recognized precisely → buttons highlighted on the user's own
   photo → steps read aloud
2. **Low confidence** — coarse match only → approximate guidance, prompt to hold
   steady / rescan; highlight is hidden rather than shown wrongly
3. **Not recognized** — friendly Vietnamese message ("try a clearer photo"), option to
   upload a photo instead of live camera, or pick the device manually from the library
4. **Errors** — every failure has a plain-Vietnamese message **plus a recovery
   action** ("try again," "rescan") — never a technical error, never a dead end

**Diagram**
- 4-step staircase descending left→right, each step showing a mini phone screen;
  green → yellow → orange → red color ramp.

**Speaker notes**
- Elderly-first means the failure paths get as much design as the happy path: large
  fonts, high-contrast option, slow speech, one message + one clear next action.
- Even backend error responses are designed as UX: they carry a Vietnamese message and
  a machine-readable recovery action that the app turns into the right button.

---

## Slide 14 — Honest Limitations

**On slide**
- **Frontal, 2D matching** — extreme angles, heavy glare, or curved panels break
  recognition
- **Small device library** — a handful of labeled appliances; real-world coverage
  needs community submissions to ramp up
- **Motion handling is conservative, not smart** — instability hides the overlay and
  asks for a rescan rather than tracking through it
- **Web demo compromises** — browser speech recognition is online-only and
  Chromium-only (the offline voice model is mobile/desktop)
- **Guidance quality bounded by labels** — the AI is only as good as each button's
  written function description
- **Not yet validated with elderly users** — usability testing with the real target
  group is the critical next step

**Diagram**
- Simple two-column "works today / known gaps" checklist.

**Speaker notes**
- Framing: each limitation is a scoping decision, not an accident — e.g. conservative
  tracking is a safety choice, and the small library is exactly what the
  human-in-the-loop pipeline (slide 11) is built to fix.

---

## Slide 15 — Thank You / Q&A

**On slide**
- **SilverTech** — *Every step points at a real button.*
- Cảm ơn! Questions?

**Anticipated questions (keep as speaker backup, not on slide)**
- *Why not train a button detector?* — Cost, data, and explainability; matching gives
  per-device support from one labeled photo and fully auditable decisions.
- *What if the AI hallucinates?* — It structurally cannot reach the user: the button
  gate rejects any step whose button isn't on the device, and off-topic questions are
  refused.
- *What about a device the app doesn't know?* — In-app labeling wizard + human review
  adds it without retraining anything.
- *Why on-device speech?* — Privacy, offline reliability, latency; the target user
  often has poor connectivity.
- *Does it work in the dark / at an angle?* — Within limits; low confidence degrades
  gracefully to rescan prompts and manual selection, never to a wrong highlight.
- *How is correctness tested?* — Contract tests on the API, known-answer geometry
  fixtures for vision, and full user-journey widget tests on the app.
