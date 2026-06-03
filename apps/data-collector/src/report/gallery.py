from __future__ import annotations

from jinja2 import Template

_TEMPLATE = Template(
    """<!doctype html><html><head><meta charset="utf-8">
<title>PanelLens Slice 1 Gallery</title>
<style>
body{font-family:sans-serif;background:#111;color:#eee}
.grid{display:flex;flex-wrap:wrap;gap:12px}
.card{width:260px;border:1px solid #333;padding:8px;border-radius:8px}
.card img{width:100%;height:180px;object-fit:contain;background:#000}
.rej{color:#f66}.brand{color:#6f6}
small{color:#999;word-break:break-all}
</style></head><body>
<h1>PanelLens Slice 1 — {{ records|length }} records</h1>
<div class="grid">
{% for r in records %}
  <div class="card">
    <img src="{{ r.image_path }}" alt="{{ r.candidate_id }}">
    <div><b>{{ r.candidate_id }}</b></div>
    <div>{{ r.query }}</div>
    <div class="brand">brand: {{ r.brand or "—" }} | {{ r.device_type_hint }}</div>
    <div>ocr: {{ r.ocr_joined }}</div>
    <div>status: {{ r.status }}
      {% if r.reject_reason %}<span class="rej">[{{ r.reject_reason }}]</span>{% endif %}
    </div>
    <small><a href="{{ r.source_url }}">{{ r.source_url }}</a></small>
  </div>
{% endfor %}
</div></body></html>""",
    autoescape=True,
)


def render_gallery(records: list[dict]) -> str:
    return _TEMPLATE.render(records=records)
