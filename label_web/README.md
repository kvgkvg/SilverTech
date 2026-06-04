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
