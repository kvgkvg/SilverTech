# Label QA/QC Pipeline — Design

**Date:** 2026-07-09
**Status:** approved, not yet implemented

## Problem

Template labels are drawn by hand in `label_web/`. That is slow, and it silently
produces bad data: the shipped Panasonic labels contain a box someone drew and
never named (`button_id: ""`), which reached the database and then the LLM
prompt as an empty button entry.

A pipeline should propose labels automatically from the two sources a human
already uses — the appliance manual and a photo of the control panel — and
flag every proposal a human needs to look at.

## Scope

**In:** generate `bbox` + `function_description` per button, in the existing
label JSON schema, with per-button QC flags.

**Out:** replacing `label_web/`. The pipeline emits a draft; a human still
reviews it. Nothing here writes to `apps/api/silvertech.sqlite3`.

## Inputs and output

| | |
|---|---|
| Input | Appliance manual: PDF with a text layer, or a scan. Both must work, mixed within one PDF. |
| Input | Panel image, e.g. `data/templates/panasonic_microwave_nn_gt35hm.png` (5712×4284). |
| Output | `data/templates/labels/<template_code>.draft.json` — the existing schema plus a `qc` field per button. |
| Output | `qc_report.json` — human/CI summary, derived from the draft, not a source of truth. |

The pipeline never overwrites a reviewed label file. It writes `.draft.json`;
a human renames it after review.

## Provider

Gemini, for both bounding-box detection and OCR of scanned pages. One provider,
one key (`GEMINI_API_KEY`), free tier.

Gemini returns `box_2d` as `[ymin, xmin, ymax, xmax]`, normalized to 0..1000
(<https://ai.google.dev/gemini-api/docs/image-understanding>). The repo schema
is `{x, y, width, height}` in absolute template pixels. The conversion therefore
does two things at once — transpose the axis order, and scale by the original
image dimensions. Getting the axis order wrong produces boxes that look
plausible in JSON and are wrong on the image. This is the pipeline's most
likely silent failure.

Because coordinates are normalized, the image does **not** need to be downscaled
by hand before the call.

Corners are rounded, then subtracted:

```python
x = round(xmin / 1000 * width);  width_px  = round(xmax / 1000 * width)  - x
y = round(ymin / 1000 * height); height_px = round(ymax / 1000 * height) - y
```

Rounding the corners keeps the right and bottom edges where the model put them.
Rounding the *difference* instead (`round((xmax - xmin) / 1000 * width)`) can
shift an edge by a pixel, and the two conventions disagree on the examples
below — pick this one and stay with it.

## Architecture

`apps/vision-tools/scripts/label_pipeline/`, alongside `offline_match.py` — an
offline tool, not wired into the API.

```
manual.pdf ──► [extract] ──► manual_text.json
panel.png  ──► [detect]  ──► detections.json
                                │
        manual_text + detections ──► [describe] ──► described.json
                                │
                                ▼
                             [qc] ──► <template>.draft.json + qc_report.json
```

```
label_pipeline/
  gemini_client.py   # the only module that touches the network
  extract.py         # PDF -> manual_text.json
  detect.py          # panel image -> detections.json
  describe.py        # manual_text + detections -> described.json
  qc.py              # rule checks, flags
  pipeline.py        # wires the four stages, CLI
  eval_detect.py     # measures detect against the gold set
```

Each stage is a pure function from file to file. No stage imports another;
`pipeline.py` composes them. Stages are cheap to re-run because only `detect`
and `extract` call the network, and both cache.

Two boundaries carry the design:

- `detect.py` does not know the manual exists.
- `describe.py` does not know the image exists.

They meet only through `button_id`. `qc.py` is the single place that decides
whether a button is trustworthy.

### CLI

```bash
python -m label_pipeline.pipeline \
  --manual data/manuals/panasonic_nn_gt35hm.pdf \
  --image  data/templates/panasonic_microwave_nn_gt35hm.png \
  --out    data/templates/labels/panasonic_microwave_nn_gt35hm_v1.draft.json
```

## Stage contracts

### extract.py

Reads the PDF's text layer per page. A page whose extracted text falls below a
character threshold is treated as a scan and sent to Gemini for OCR. Both modes
can occur in one document.

```json
{
  "source": "data/manuals/panasonic_nn_gt35hm.pdf",
  "pages": [
    { "page": 4, "mode": "text_layer", "text": "Nút Vi sóng: chọn công suất..." },
    { "page": 9, "mode": "gemini_ocr", "text": "..." },
    { "page": 11, "mode": "gemini_ocr", "text": null, "error": "429 after 5 retries" }
  ]
}
```

`mode` is recorded per page because the first question about a wrong
description is always whether that page was read or OCR'd. A failed page does
not fail the stage.

### detect.py

One Gemini call on the panel image. Also detects two special regions, `logo`
and `panel`, which populate the template's `logo_bbox` and `panel_bbox`.

```json
{
  "image": { "path": "...png", "width": 5712, "height": 4284 },
  "model": "gemini-3-flash",
  "prompt_version": "sha256:ab12…",
  "detections": [
    {
      "button_id": "micro_power",
      "label_text": "Micro Power",
      "box_2d": [604, 783, 772, 891],
      "bbox_template_coordinates": { "x": 4472, "y": 2588, "width": 617, "height": 719 },
      "confidence": 0.86
    }
  ]
}
```

The raw `box_2d` is kept next to the converted box on purpose: when a box is
wrong, the artifact alone distinguishes "the model guessed wrong" from "our
conversion is wrong", without spending another API call.

`button_id` is derived by slugging `label_text`, using the same rules as
`label_web/app.js`'s `slug()`. A button with no text — an icon-only arrow —
gets `button_id: null` and a QC flag. **The model is never asked to invent an
id.** A wrong id breaks the `button_id` validation invariant in
`services/guidance_service.py`, which is the system's core correctness gate.

### describe.py

Given `manual_text.json` and the detected ids, produces the Vietnamese fields:

```json
{
  "button_id": "micro_power",
  "vietnamese_name": "Vi sóng",
  "function_description": "chọn mức công suất vi sóng",
  "manual_evidence": { "page": 4, "quote": "Nhấn Micro Power để chọn công suất." }
}
```

`manual_evidence` turns "the model invented a description" from a silent bug
into a checkable one: QC verifies the quote appears in `manual_text.json`.

### qc.py

Flags, never deletes. Every detected button reaches the draft.

Per button:

| id | condition |
|---|---|
| `missing_id` | `button_id` null or blank |
| `missing_name` | `vietnamese_name` blank |
| `raw_id_in_text` | `function_description` contains the raw `button_id` |
| `no_evidence` | `manual_evidence.quote` not found in `manual_text.json` |
| `low_confidence` | `confidence` below the configured threshold |
| `bbox_out_of_bounds` | box exceeds image bounds, or `width`/`height` ≤ 0 |
| `bbox_degenerate` | box area below ~0.1% of image area |
| `bbox_outside_panel` | box centre lies outside `panel_bbox` |

Per template:

| id | condition |
|---|---|
| `duplicate_id` | two buttons share a `button_id` |
| `bbox_overlap` | IoU between two boxes exceeds the threshold |
| `manual_button_missing` | the manual names a button that `detect` did not find |
| `detected_not_in_manual` | `detect` found a button the manual never mentions |

The last two are why the pipeline needs both inputs. The image alone cannot
reveal a missing button; the manual alone cannot say where a button is. Both
only flag: manuals omit minor buttons, and photos crop corners.

`raw_id_in_text` mirrors a bug already fixed on the API side, where the LLM
echoed `time_1_min` into spoken text and gTTS read it aloud as "tam gạch dưới
một gạch dưới min".

Output, per button, added to the existing schema:

```json
"qc": { "status": "pass", "issues": [], "confidence": 0.86 }
```

`status` is `pass` or `flag`. The field lives inside the button so `label_web/`
reads one file to paint its warnings. `seed.py` inserts by column name and
ignores `qc`.

## Errors and cost

`gemini_client.py` owns everything that can go wrong on the network.

- **Cache before call.** Key is `sha256(image or page bytes) + model + prompt_version`, stored under `.cache/label_pipeline/` (gitignored). Re-running the pipeline after editing a QC rule costs zero requests.
- **`prompt_version` is the hash of the prompt string**, not a hand-maintained number, so an edited prompt cannot silently read a stale cache entry.
- **Retry with backoff** on 429 and 5xx. The Gemini free tier rate-limits well below a 40-page manual.
- **A failed page fails that page.** A failed `detect` fails the run — with no boxes there is nothing to emit.
- **Unparseable model JSON is not retried blindly.** The raw response is written to the artifact and the stage raises, mirroring `_parse_json_content` in `services/llm_service.py`.

## Testing

Unit tests use JSON fixtures and never call the network, following
`apps/vision-tools/tests`, which tests the matcher on deterministic keypoint
arrays rather than real images.

The first test covers coordinate conversion:

```python
def test_box_2d_maps_y_first_not_x_first():
    box = to_bbox([100, 500, 200, 750], width=5712, height=4284)
    assert box == {"x": 2856, "y": 428, "width": 1428, "height": 429}
```

Asserting each field separately, on a non-square image, is what catches a
transposed axis. The `bbox_out_of_bounds` rule catches a transposition only when
the resulting coordinate happens to exceed the image; a small box near the
top-left corner survives it. A second case uses the Electrolux image (2560×810),
whose 3.2:1 ratio exposes the error more sharply.

Also: one test per QC rule (valid button passes, broken button is flagged, and
no rule ever drops a button); `extract.py`'s threshold branch between
`text_layer` and `gemini_ocr`; `gemini_client.py`'s cache hit/miss and retry,
driven by a fake transport.

## Evaluation

Gold set: the two reviewed label files — Panasonic (15 labeled buttons) and
Electrolux (11). 26 buttons total.

`eval_detect.py` matches detections to gold buttons by maximum IoU, greedy
one-to-one, threshold 0.5. It reports:

- **precision / recall @ IoU 0.5** — extra buttons, missed buttons
- **mean IoU** over matched pairs — how tight the boxes are
- **`button_id` accuracy** over matched pairs — whether the slug matches the human's id

These measure three different things. A model can reach 100% recall with a mean
IoU of 0.55: it sees every button and boxes them loosely. Collapsing them into
one score hides that.

With n=26, one button is 4%. The evaluation therefore prints a **per-button
table**, not only the three aggregates; comparing two models on the aggregates
alone would be self-deception at this sample size.

Run by hand, not in CI — CI calling the API would burn the free-tier quota.

**Recorded prediction, to check against the first real run:** the model will
miss icon-only buttons (the up/down arrows), and `button_id` accuracy will come
in below recall, because `up` and `down` carry no text to slug. If the first
run does not show this, an assumption above is wrong and the design needs
another look.

**No hard pass/fail threshold.** The pipeline produces a draft for a human.
"Good enough" means correcting is cheaper than labeling from scratch. The
numbers exist to compare two models or two prompts, not to gate a build.

## Open questions

- `data/manuals/` does not exist yet. The first real manual PDF must be added before the pipeline can run end to end.
- `brand` and `model_name` for the `device` block are read from the manual's cover page. If a manual omits them, the operator supplies them via CLI flags.
