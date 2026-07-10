# SilverTech Template Labeler

Static browser tool for labeling appliance template images and exporting rows
for the current SQLite schema.

## Run

Open `index.html` directly in a browser, or serve the folder:

```bash
cd label_web
python3 -m http.server 5174
```

Then open <http://127.0.0.1:5174>.

## Output

The export contains:

- one `devices` row
- one `templates` row with `panel_bbox` and `logo_bbox`
- many `buttons` rows with `bbox_template_coordinates`

Use **Copy SQL** to paste directly into `sqlite3 apps/api/silvertech.sqlite3`,
or **Download JSON** to keep labels for review before converting to seed data.

Vietnamese text fields such as `vietnamese_name` and
`function_description` accept spaces and Vietnamese diacritics. IDs such as
`button_id`, `device_id`, and `template_id` should still use stable ASCII
snake_case values.

## Reviewing user submissions

`review.html` lists submissions filed by the mobile wizard, draws their boxes
over the panel photo, lets you fix them, and accepts or rejects the submission.
Accepting writes a real template: `devices`, `templates`, `buttons` and
`button_offsets`, plus a copy of the photo under `data/templates/`.

```bash
SILVERTECH_ADMIN_TOKEN=<a long random string> make run-api
python3 -m http.server 8080 --directory label_web
```

Open `http://localhost:8080/review.html?token=<the same string>`. The token is
kept in `localStorage` after the first load.

Serve the page; do not open it as a `file://` URL. `file://` sends
`Origin: null`, which the API's CORS policy rejects. Override the backend with
`?api=https://...` if it is not on `http://localhost:8000`.
