from __future__ import annotations

from typing import Any

from app.models.common import decode_json
from app.storage.database import db_session


def _template_summary(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "brand": row["brand"],
        "appliance_type": row["appliance_type"],
        "template_code": row["template_code"],
        "version": row["version"],
        "status": row["status"],
        "template_image_url": row["template_image_url"],
        "logo_bbox": decode_json(row["logo_bbox"]),
        "panel_bbox": decode_json(row["panel_bbox"]),
        "feature_descriptor_url": row["feature_descriptor_path"],
    }


def list_candidates(brand: str | None, appliance_type: str | None) -> list[dict[str, Any]]:
    query = """
        SELECT t.*, d.brand, d.appliance_type
        FROM templates t
        JOIN devices d ON d.id = t.device_id
        WHERE t.status = 'official' AND d.status = 'active'
    """
    params: dict[str, Any] = {}
    if brand:
        query += " AND lower(d.brand) = lower(:brand)"
        params["brand"] = brand
    if appliance_type:
        query += " AND d.appliance_type = :appliance_type"
        params["appliance_type"] = appliance_type
    query += " ORDER BY d.brand, t.template_code"
    with db_session() as conn:
        return [_template_summary(row) for row in conn.execute(query, params).fetchall()]


def get_template(template_id: str) -> dict[str, Any] | None:
    with db_session() as conn:
        row = conn.execute(
            """
            SELECT t.*, d.brand, d.appliance_type
            FROM templates t JOIN devices d ON d.id = t.device_id
            WHERE t.id = :id AND t.status = 'official'
            """,
            {"id": template_id},
        ).fetchone()
        if row is None:
            return None
        buttons = conn.execute(
            "SELECT * FROM buttons WHERE template_id = :template_id ORDER BY button_id",
            {"template_id": template_id},
        ).fetchall()
    detail = _template_summary(row)
    detail["buttons"] = [
        {
            "button_id": b["button_id"],
            "label": b["label"],
            "vietnamese_name": b["vietnamese_name"],
            "function_description": b["function_description"],
            "bbox_template_coordinates": decode_json(b["bbox_template_coordinates"]),
            "polygon_template_coordinates": decode_json(b["polygon_template_coordinates"]),
            "button_type": b["button_type"],
        }
        for b in buttons
    ]
    return detail


def valid_button_ids(template_id: str) -> set[str]:
    template = get_template(template_id)
    if template is None:
        return set()
    return {button["button_id"] for button in template["buttons"]}
