# Submission Promotion & Admin Review — Design

**Date:** 2026-07-10
**Status:** approved, not yet implemented

## Problem

The mobile add-device wizard collects a panel photo, a logo box, and a labelled
button box per button, then `POST /api/submissions` files them in the
`submissions` table. Nothing reads that table.

`review_submission` flips a status column and returns `template_id: None`
(`app/services/review_service.py:18`). No code path inserts into `templates`.
So a device a user adds can never be recognised: `run_logo_anchor` only
considers rows from `list_candidates`, which filters
`t.status = 'official' AND d.status = 'active'`.

`POST /api/admin/submissions/{id}/review` has no client either.
`apps/mobile/lib/templates/admin_review_screen.dart` is five lines holding a
DTO, no widget.

The contract already describes the intended behaviour: `openapi.yaml:204`
declares a `template_id` in the review response, and `SubmissionReview` already
carries `edited_template` (`app/schemas/templates.py:122`). The implementation
never caught up.

## Scope

This is spec 1 of 2.

**In:** promote a reviewed submission into `devices` + `templates` + `buttons` +
`button_offsets`; two admin read endpoints; a review page in `label_web/`;
token auth on `/api/admin`.

**Out:** the mobile side. The wizard keeps filing submissions exactly as it does
now. Showing a "pending review" badge on the device card, and polling for the
resulting `template_id`, is spec 2. It is written after this contract runs.

**Out:** writing brand logos to `data/brands/`. Not needed —
`_detect_best_template` (`logo_anchor_service.py:248`) crops the logo out of the
template's own image using `logo_bbox`, and only falls back to the SIFT gallery
path when it exists. A promoted template is detectable without touching
`data/brands/`.

## What a template needs to be detectable

Discovered by reading `run_logo_anchor`. All five must hold:

| | Source |
|---|---|
| `devices` row, `status = 'active'` | `list_candidates` filter |
| `templates` row, `status = 'official'` | `list_candidates` filter |
| `templates.logo_bbox` not null | `logo_anchor_service.py:235` |
| `button_offsets` rows | `logo_anchor_service.py:237`, else 409 `"no button_offsets; run compute_logo_offsets.py first"` |
| an image readable at `ROOT / template_image_url` | `_load_template_assets` |

The fourth is the one this feature exists to supply. Nothing in the API writes
`button_offsets` today; only `apps/vision-tools/scripts/compute_logo_offsets.py`
does, by hand.

## Identity

Server mints every id from the submission id. Client-supplied ids
(`autoDeviceId`, `autoTemplateId` in `main.dart:1511`) are discarded.

```
sid         = submission_id.replace('-', '')[:8]
device_id   = f"device_{sid}"
template_id = f"template_{sid}"
button row  = f"btn_{sid}_{button_id}"
```

`autoDeviceId` is `device_{brand}_{type}_01` — no model name. Two users
submitting the same brand and appliance type collide on the primary key. Letting
a client name a row in `templates` also means a typo can aim at someone else's
template. Promotion is a server action; the server owns the identity.

`template_code` keeps the client's slug, so the table stays greppable, and
`list_candidates` still orders by it. `version` is always 1: one submission, one
template. A second `accept` on the same submission is a 409, which makes
idempotency a single check rather than a version-bump branch.

Eight hex characters is 4.3 billion values, and two submissions could in
principle share a prefix. They would collide on a primary key inside the
transaction, raising `IntegrityError`, rolling back, and surfacing as a 409 with
nothing written. Wrong message, no damage.

## Image path

`promote_submission` copies `data/submissions/<uuid>.<ext>` to
`data/templates/template_<sid>.<ext>`, and points `template_image_url` at the
copy. `data/submissions/` stays a queue; deleting it must not kill a live
template.

**The filename contains no client-supplied string.** An earlier draft of this
design named the copy after `template_code`, which arrives from the client: a
submission whose `template_code` is `../../../home/lesliu/.ssh/authorized_keys`
would have escaped the repo. The extension comes from the whitelist already in
`submissions.py:15` (`.jpg .jpeg .png .webp`), matched against the stored file's
suffix, not against any name in the request.

## Promotion service

New `app/services/promotion_service.py`, one public function:

```python
def promote_submission(conn, submission_id: str, labels: dict) -> str:
    """Insert devices/templates/buttons/button_offsets from reviewed labels.
    Returns the new template_id. The caller owns the transaction."""
```

It takes an open connection rather than opening its own. `review_service`
already runs inside `db_session()`, which commits on success and rolls back on
exception (`storage/database.py:141`). A failed copy or a bad bbox must not
leave an orphan `devices` row.

Statuses are overwritten, not trusted: `devices.status = 'active'`,
`templates.status = 'official'`. `_buildLabels` sends `'submitted'` for the
device (`main.dart:1569`), which violates
`CHECK (status IN ('active', 'archived'))` and would fail the insert.

Offsets come from `compute_button_offsets(logo_bbox, buttons)` in
`scripts.logo_anchor`. It is pure arithmetic — no OpenCV, no image. The
`sys.path.insert` block that makes `apps/vision-tools` importable already exists
at `logo_anchor_service.py:17-20`; it moves to a shared module rather than being
copied.

### Rejections

`promote_submission` refuses; it never repairs.

| Condition | Consequence if allowed |
|---|---|
| `logo_bbox` is null | `run_logo_anchor` raises 409 `"template has no logo_bbox"` |
| `buttons` empty | nothing to project |
| duplicate `button_id` | violates `UNIQUE(template_id, button_id)` |
| any bbox `width <= 0` or `height <= 0` | degenerate projection |
| `logo_bbox.width <= 0` | `compute_button_offsets` raises `ValueError("logo_bbox width must be positive")` |
| image unreadable | `_load_template_assets` raises 500 at detect time |
| submission not `pending` | double promotion |

Each maps to `friendly_error(400 or 409, <Vietnamese>, "try_again")`, as
everywhere else in the API.

A button box outside the image bounds is *not* rejected. `_buildLabels` already
clamps to `photoSize`, and `label_pipeline/qc.py` flags `bbox_out_of_bounds`
rather than dropping the button — a button dropped is a button nobody reviews.

## Review service

```python
def review_submission(submission_id, decision, reviewer_note, edited_template=None) -> dict
```

- `reject` → status `rejected`, `template_id: None`. Unchanged.
- `accept` → promote using the stored `proposed_labels_json`.
- `edit` → promote using `edited_template`. Missing it is a 400.

One `db_session()` spans the status update and the promotion.

Returns `{"submission_id", "status", "template_id"}` — what `openapi.yaml:204`
already promises.

## Admin auth

`/api/admin` is currently unauthenticated. Today that is harmless: review writes
one column nobody reads. After this change the same endpoint writes the
`templates` table the runtime serves from, and copies files onto the host's
disk. The backend is reachable at a permanent public ngrok domain.

A FastAPI dependency on the `/api/admin` router requires header `X-Admin-Token`
to equal `SILVERTECH_ADMIN_TOKEN`. **When the variable is unset the router
returns 503, not 200.** Default closed: forgetting to configure it must not be
the thing that opens the door.

`SILVERTECH_ADMIN_TOKEN=` is added to `.env.example` with a comment. `env_loader`
only sets a key absent from `os.environ` (`services/env_loader.py:20`), so a
running `--reload` server does not pick up a changed `.env`; the README note
says restart.

This does not make the deployment safe. `POST /api/submissions` remains open and
unrated, and `POST /api/query` bills a real OpenRouter key. The tunnel stays off
outside demos.

## Endpoints

Added to `app/api/admin_submissions.py`, under the existing `/api/admin` prefix,
behind the token dependency:

```
GET /api/admin/submissions?status=pending
    → [{id, brand, appliance_type, image_url, status, created_at}]

GET /api/admin/submissions/{id}
    → the above + proposed_labels_json (decoded), reviewer_note
```

No pagination. The demo queue is countable on one hand.

`openapi.yaml` gains both, and its existing `POST /api/submissions` entry is
corrected: it declares `multipart/form-data`, but `submissions.py:19` accepts
JSON (`SubmissionCreate`) and takes the image through a separate
`POST /api/submissions/image`. The contract has been wrong since it was written,
and `tests/contract/` stayed green — evidence those tests do not check what they
appear to check.

## Review page

`label_web/review.html` + `review.js`, beside the existing `index.html`.
`app.js` (585 lines) is left alone; it serves the offline labelling flow.

1. `GET /api/admin/submissions?status=pending` fills a list.
2. Selecting one loads `GET /{id}`, draws `image_url` on a canvas, overlays
   `logo_bbox` and each button bbox.
3. The admin drags boxes and edits names. An elderly user's boxes are crooked;
   a reviewer who cannot fix them can only reject, and a rejected user does not
   come back.
4. **Duyệt** posts `{decision: 'edit', edited_template}` when anything changed,
   `{decision: 'accept'}` when nothing did.
   **Từ chối** posts `{decision: 'reject', reviewer_note}`.
5. The returned `template_id` is displayed.

The box-drawing and dragging code is extracted from `app.js` into `boxes.js` and
imported by both pages, rather than copied.

CORS needs no change: served from `python -m http.server`, the origin is
`http://localhost:<port>`, which matches `_DEV_ORIGIN_REGEX` in `app/main.py`.
Opening `review.html` as a `file://` URL sends `Origin: null` and fails — the
README says to run the server. The panel photo loads from
`http://localhost:8000/data/submissions/...`, already mounted as `StaticFiles`.

The API base comes from `?api=` on the URL, defaulting to
`http://localhost:8000`. The admin token is read from `?token=` and kept in
`localStorage`. Admin does not go through ngrok.

## Testing

`apps/api/tests/test_promotion.py`, against a temporary database:

- promotion writes all four tables, with the right button count
- `devices.status == 'active'` and `templates.status == 'official'` — without
  both, `list_candidates` filters the row straight back out
- `button_offsets` match a direct call to `compute_button_offsets`
- null `logo_bbox` → 400
- duplicate `button_id` → 400
- accepting twice → 409, **and the tables are unchanged** (proves the rollback)
- `edit` without `edited_template` → 400
- `reject` creates no template
- `/api/admin` without `X-Admin-Token` → 401; with `SILVERTECH_ADMIN_TOKEN`
  unset → 503

`apps/api/tests/test_promoted_template_is_detectable.py` — the only test that
shows the feature does anything:

> file a submission whose image is `data/templates/panasonic_microwave_nn_gt35hm.png`
> with a `logo_bbox` and three buttons → accept → `run_logo_anchor(None, <that
> same image>)` returns the new `template_id` with `accepted == True`.

It runs without `data/brands/` because `_detect_best_template` does not need it.
This is the one test that catches a forgotten `button_offsets` write — the
omission that made the whole submission flow inert.

`tests/contract/` extends to the corrected `openapi.yaml`.

## Docs

- `docs/backend-api.md` — the two new endpoints, the token header.
- `docs/known-limitations.md` — drop the claim that submissions are inert; add
  that `/api/admin` is token-only and the tunnel must stay off.
- `label_web/README.md` — how to serve the page and pass `?api=` and `?token=`.

No new top-level doc. `docs/label-qa-pipeline.md` stays as it is: that pipeline
still writes `.draft.json` for a human, and still never touches the database.
The two paths into `templates` — offline pipeline plus `make seed-api`, and now
user submission plus admin review — are described where each lives.

## Follow-up, not in this spec

The device library disappears on browser refresh.
`JsonFileDeviceLibraryStore` (`main.dart:163`) persists through
`getApplicationDocumentsDirectory()`, and `pubspec.lock` has no
`path_provider_web`. The call throws, and `unawaited(_restoreDevices())` swallows
it. Unrelated to promotion; fix separately.
