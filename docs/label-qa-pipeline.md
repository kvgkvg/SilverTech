# Label QA/QC pipeline

Turns an appliance manual PDF and a control-panel photo into a *draft* label file:
one bounding box and one Vietnamese description per button, with a QC flag on every
button a human must re-check.

It emits a proposal. A human still reviews it. Nothing here writes to the database.

## Run it

```bash
conda activate silvertech
export GEMINI_API_KEY=...            # or put it in .env

PYTHONPATH=apps/vision-tools python -m scripts.label_pipeline.pipeline \
  --manual data/manuals/panasonic_nn_gt35hm.pdf \
  --image  data/templates/panasonic_microwave_nn_gt35hm.png \
  --brand Panasonic --model-name NN-GT35HM --appliance-type microwave \
  --display-name "Lò vi sóng Panasonic NN-GT35HM" \
  --out data/templates/labels/panasonic_microwave_nn_gt35hm_v1.draft.json
```

Then open the draft in `label_web/`, fix every button whose `qc.status` is `flag`,
and rename the file to drop `.draft`. `seed.py` deliberately skips any file ending
in `.draft.json` or `.qc_report.json` when it globs the labels directory, so a
draft is invisible to `make seed-api` until that rename makes it an ordinary
`.json` file.

The CLI refuses an `--out` that is not a `.draft.json`. A reviewed label file is a
human artifact.

Full flag list (`pipeline.py`'s `main()`):

| Flag | Required | Notes |
|---|---|---|
| `--manual` | yes | appliance manual PDF |
| `--image` | yes | control panel image |
| `--out` | yes | must end in `.draft.json`, else exit code 2 |
| `--brand` | yes | |
| `--model-name` | yes | |
| `--appliance-type` | yes | |
| `--display-name` | no | defaults to `"{brand} {model_name}"` |
| `--template-code` | no | defaults to a slug of brand/appliance/model + `_v1` |
| `--model` | no | Gemini model id, defaults to `gemini-3.5-flash` |
| `--confidence-threshold` | no | defaults to `0.5`, feeds the `low_confidence` QC flag |

A button's row `id` is `btn_{template_code}_{button_id}` (`_v1` included), matching
the id `label_web/app.js:286` recomputes on save — the pipeline and the review UI
must agree on this format or a re-save silently mints a second row.

## Stages

| Stage | In | Out | Network |
|---|---|---|---|
| `extract` | manual PDF | `manual_text.json` | only for scanned pages |
| `detect` | panel image | `detections.json` | one call |
| `describe` | manual text + ids | `described.json` | one call |
| `qc` | the above | `<template_code>.draft.json`, `<template_code>.qc_report.json` | none |

Intermediates land in `<out_dir>/.pipeline/<image_stem>/` (gitignored via `.pipeline/`
in `.gitignore`). `detect` does not know the manual exists; `describe` does not know
the image exists. They meet only through `button_id`.

The draft (`data/templates/labels/*.draft.json`, gitignored) and its QC report
(`data/templates/labels/*.qc_report.json`, gitignored) are written next to each
other — `run()` derives the report's name by replacing `.draft.json` with
`.qc_report.json` on the `--out` path, so it is never a bare `qc_report.json`.

## Cost

Every Gemini call is cached under `.cache/label_pipeline/` (also gitignored), keyed
by the model, a hash of the prompt, and a hash of the image. Re-running after editing
a QC rule costs zero requests. Editing a prompt invalidates only that prompt's
entries. The default model is `gemini-3.5-flash`; override it per-run with `--model`.

## QC flags

Per button: `missing_id`, `missing_name`, `raw_id_in_text`, `no_evidence`,
`low_confidence`, `bbox_out_of_bounds`, `bbox_degenerate`, `bbox_outside_panel`.

Per template: `duplicate_id`, `bbox_overlap`, `manual_button_missing`,
`detected_not_in_manual`.

QC flags; it never deletes. A button dropped here is a button nobody reviews.

`raw_id_in_text` exists because the API once fed a raw `button_id` to TTS, and gTTS
read `time_1_min` aloud as "tam gạch dưới một gạch dưới min".

`manual_button_missing` and `detected_not_in_manual` are why the pipeline needs both
inputs: the image cannot reveal a button that is missing, and the manual cannot say
where a button is. Both only warn — manuals omit minor buttons, and photos crop corners.

## Measuring detect

```bash
PYTHONPATH=apps/vision-tools python -m scripts.label_pipeline.eval_detect \
  --detections data/templates/labels/.pipeline/panasonic_microwave_nn_gt35hm/detections.json \
  --gold data/templates/labels/panasonic_microwave_nn_gt35hm_v1.json
```

Reports precision, recall, mean IoU and `button_id` accuracy separately, plus a
per-button table. They measure different things: a model can reach full recall with a
mean IoU of 0.55, seeing every button and boxing them loosely.

There is no pass/fail threshold. "Good enough" means correcting the draft is cheaper
than labeling from scratch. Run it by hand — in CI it would burn the free-tier quota.

The gold set is the two reviewed label files: Panasonic (16 buttons, panel photo is a
`.png`) and Electrolux (11 buttons, panel photo is a `.jpg`) — 27 buttons total.
Electrolux's `button_id`s are `"1"`…`"11"`: position numbers from a manual diagram,
not slugs of panel text. They are excluded from `button_id` accuracy, and the excluded
count is printed beside it.

## Limitations

- `pypdf` cannot rasterize a page directly, so a scanned page is OCR'd from its
  largest embedded image rather than a full-page render; a page with none is
  recorded as an error and skipped.
- `data/manuals/` ships empty. Add the manual PDF before the first run.
- `brand`, `model_name` and `appliance_type` come from CLI flags, not from the manual
  cover page.
