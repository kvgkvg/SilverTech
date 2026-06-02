# Research: SilverTech Camera Voice Guidance

## Decision: Flutter for Mobile MVP

**Rationale**: Flutter provides a single mobile codebase, mature Android
support, camera access, custom overlay rendering, platform TTS access, and a
good path to iOS later without changing the UX model.

**Alternatives considered**: React Native is viable, but native/OpenCV bridge
work and high-frequency overlay rendering are simpler to keep predictable in
Flutter for this MVP. Native Android alone would reduce cross-platform reuse.

## Decision: OpenCV On-Device Vision Module

**Rationale**: The constitution requires logo-guided template matching with
feature matching and geometric projection. OpenCV provides ORB/SIFT,
BFMatcher/FLANN, RANSAC homography/affine estimation, reprojection error
calculation, and optical flow primitives without training a custom detector.

**Alternatives considered**: Custom model training is out of MVP scope and
would require more labeled data. Server-side frame processing would increase
latency and privacy exposure.

## Decision: FastAPI Backend

**Rationale**: FastAPI is suitable for a small typed API with OpenAPI contracts,
Pydantic schema validation, Python-based vision tooling reuse, and simple STT
and LLM provider adapters.

**Alternatives considered**: Node.js is viable, but Python better matches the
offline vision proof of concept and testing workflow for OpenCV utilities.

## Decision: SQLite for MVP, PostgreSQL-Compatible Schema

**Rationale**: SQLite keeps local demos and development lightweight while still
supporting relational constraints needed for `button_id` validation and review
status. The schema will avoid SQLite-only behavior so it can move to PostgreSQL
for deployment.

**Alternatives considered**: PostgreSQL from day one is stronger for production
but adds operational overhead before the MVP validates the pipeline.

## Decision: Provider-Adapter STT and LLM Integration

**Rationale**: Vietnamese STT quality and latency may vary by provider. The
backend should wrap Google STT, Zalo ASR, or another Vietnamese-capable service
behind a small interface. The LLM adapter should support Gemini Flash,
GPT-4o-mini, or another low-latency model while enforcing the same output
schema and `button_id` validation.

**Alternatives considered**: Hard-coding one provider is faster initially but
raises vendor risk. Full offline STT/LLM is out of MVP scope.

## Decision: Platform TTS for MVP

**Rationale**: Built-in Android/iOS TTS is enough for optional spoken guidance
and avoids introducing another network dependency for the MVP.

**Alternatives considered**: Cloud TTS may produce better voices but is not
necessary for proving the guidance workflow.

## Decision: Confidence-Gated Matching

**Rationale**: The app should only accept a template when feature match quality,
inlier count, inlier ratio, reprojection error, and geometry plausibility all
meet thresholds. If any critical gate fails, the app must ask the user to
rescan, move closer, reduce glare, scan wider, or manually select.

**Alternatives considered**: A single match score is simpler but too brittle for
similar panels and poor camera conditions.

## Decision: Reviewed Template Database as Runtime Authority

**Rationale**: Button guidance is only safe when every highlighted button comes
from reviewed template metadata. Official templates and submitted templates must
remain separate until review.

**Alternatives considered**: Letting submissions immediately expand coverage
would improve breadth but violates the button-accuracy principle.
