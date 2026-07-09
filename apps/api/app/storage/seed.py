from __future__ import annotations

import json

from app.models.common import encode_json
from app.storage.database import ROOT
from app.storage.database import db_session, initialize_database
from app.storage.seed_data import BUTTONS, DEVICES, NOW, TEMPLATES


def is_labeled_button(button: dict) -> bool:
    """A button is usable only once it has both an id and a name to speak."""
    return bool(str(button.get("button_id", "")).strip()) and bool(
        str(button.get("vietnamese_name", "")).strip()
    )


def seed_database() -> None:
    initialize_database()
    with db_session() as conn:
        for device in DEVICES:
            conn.execute(
                """
                INSERT OR REPLACE INTO devices
                (id, brand, appliance_type, model_name, display_name, status, created_at, updated_at)
                VALUES (:id, :brand, :appliance_type, :model_name, :display_name, :status, :created_at, :updated_at)
                """,
                {**device, "created_at": NOW, "updated_at": NOW},
            )
        for template in TEMPLATES:
            row = {
                **template,
                "logo_bbox": encode_json(template["logo_bbox"]),
                "panel_bbox": encode_json(template["panel_bbox"]),
                "created_at": NOW,
                "updated_at": NOW,
            }
            conn.execute(
                """
                INSERT OR REPLACE INTO templates
                (id, device_id, template_code, template_image_url, logo_bbox, panel_bbox,
                 feature_descriptor_path, version, status, created_at, updated_at)
                VALUES (:id, :device_id, :template_code, :template_image_url, :logo_bbox, :panel_bbox,
                        :feature_descriptor_path, :version, :status, :created_at, :updated_at)
                """,
                row,
            )
        for button in BUTTONS:
            row = {
                **button,
                "bbox_template_coordinates": encode_json(button["bbox_template_coordinates"]),
                "polygon_template_coordinates": encode_json(button["polygon_template_coordinates"]),
                "created_at": NOW,
                "updated_at": NOW,
            }
            conn.execute(
                """
                INSERT OR REPLACE INTO buttons
                (id, template_id, button_id, label, vietnamese_name, function_description,
                 bbox_template_coordinates, polygon_template_coordinates, button_type, created_at, updated_at)
                VALUES (:id, :template_id, :button_id, :label, :vietnamese_name, :function_description,
                        :bbox_template_coordinates, :polygon_template_coordinates, :button_type, :created_at, :updated_at)
                """,
                row,
            )
        for label_path in sorted((ROOT / "data" / "templates" / "labels").glob("*.json")):
            label = json.loads(label_path.read_text(encoding="utf-8"))
            device = label["device"]
            template = label["template"]
            conn.execute(
                """
                INSERT OR REPLACE INTO devices
                (id, brand, appliance_type, model_name, display_name, status, created_at, updated_at)
                VALUES (:id, :brand, :appliance_type, :model_name, :display_name, :status, :created_at, :updated_at)
                """,
                device,
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO templates
                (id, device_id, template_code, template_image_url, logo_bbox, panel_bbox,
                 feature_descriptor_path, version, status, created_at, updated_at)
                VALUES (:id, :device_id, :template_code, :template_image_url, :logo_bbox, :panel_bbox,
                        :feature_descriptor_path, :version, :status, :created_at, :updated_at)
                """,
                {
                    **template,
                    "logo_bbox": encode_json(template["logo_bbox"]),
                    "panel_bbox": encode_json(template["panel_bbox"]),
                },
            )
            for button in label["buttons"]:
                if not is_labeled_button(button):
                    # The labelling tool saves boxes that were drawn but never
                    # named. Seeding them would offer the LLM an unusable button.
                    print(
                        f"skipping unlabeled button {button['id']} "
                        f"in {label_path.name}"
                    )
                    continue
                conn.execute(
                    """
                    INSERT OR REPLACE INTO buttons
                    (id, template_id, button_id, label, vietnamese_name, function_description,
                     bbox_template_coordinates, polygon_template_coordinates, button_type, created_at, updated_at)
                    VALUES (:id, :template_id, :button_id, :label, :vietnamese_name, :function_description,
                            :bbox_template_coordinates, :polygon_template_coordinates, :button_type, :created_at, :updated_at)
                    """,
                    {
                        **button,
                        "bbox_template_coordinates": encode_json(
                            button["bbox_template_coordinates"]
                        ),
                        "polygon_template_coordinates": encode_json(
                            button["polygon_template_coordinates"]
                        ),
                    },
                )
        # INSERT OR REPLACE cannot remove rows a previous seed wrote, so drop any
        # unlabeled button left behind by an older run of this script.
        conn.execute(
            "DELETE FROM buttons WHERE trim(button_id) = '' OR trim(vietnamese_name) = ''"
        )


if __name__ == "__main__":
    seed_database()
    print("Seeded SilverTech MVP templates")
