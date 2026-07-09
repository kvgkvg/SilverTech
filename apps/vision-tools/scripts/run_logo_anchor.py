"""Run the logo-anchored pipeline on a real frame image against a DB template.

Usage:
    PYTHONPATH=apps/vision-tools python apps/vision-tools/scripts/run_logo_anchor.py \
        --frame path/to/photo.jpg \
        --template-id template_panasonic_microwave_nn_gt35hm_v1 \
        [--db apps/api/silvertech.sqlite3] [--out out.png]

Draws detected logo (red), coarse logo projection (dashed yellow), refined
homography projection (green) onto the frame and prints the result summary.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import numpy as np

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None

from scripts.logo_anchor import offsets_from_rows
from scripts.logo_anchor_match import detect_logo, match_with_logo_anchor

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = ROOT / "apps" / "api" / "silvertech.sqlite3"


def load_template(conn: sqlite3.Connection, template_id: str) -> dict:
    row = conn.execute(
        "SELECT * FROM templates WHERE id = :id", {"id": template_id}
    ).fetchone()
    if row is None:
        raise SystemExit(f"template not found: {template_id}")
    buttons = {
        b["button_id"]: json.loads(b["bbox_template_coordinates"])
        for b in conn.execute(
            "SELECT button_id, bbox_template_coordinates FROM buttons WHERE template_id = :id",
            {"id": template_id},
        ).fetchall()
    }
    offsets = offsets_from_rows(
        [
            dict(r)
            for r in conn.execute(
                "SELECT button_id, dx, dy, dw, dh FROM button_offsets WHERE template_id = :id",
                {"id": template_id},
            ).fetchall()
        ]
    )
    return {
        "logo_bbox": json.loads(row["logo_bbox"]) if row["logo_bbox"] else None,
        "image_url": row["template_image_url"],
        "buttons": buttons,
        "offsets": offsets,
    }


def draw_quad(img, corners, color, thickness=3, dashed=False):
    pts = [(int(c["x"]), int(c["y"])) for c in corners]
    for i in range(4):
        p1, p2 = pts[i], pts[(i + 1) % 4]
        if dashed:
            steps = 8
            for k in range(0, steps, 2):
                a = (
                    int(p1[0] + (p2[0] - p1[0]) * k / steps),
                    int(p1[1] + (p2[1] - p1[1]) * k / steps),
                )
                b = (
                    int(p1[0] + (p2[0] - p1[0]) * (k + 1) / steps),
                    int(p1[1] + (p2[1] - p1[1]) * (k + 1) / steps),
                )
                cv2.line(img, a, b, color, thickness)
        else:
            cv2.line(img, p1, p2, color, thickness)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frame", required=True)
    parser.add_argument("--template-id", required=True)
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--out", default="logo_anchor_out.png")
    args = parser.parse_args()

    if cv2 is None:
        raise SystemExit("OpenCV required: run inside the silvertech conda env")

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    tpl = load_template(conn, args.template_id)
    conn.close()
    if tpl["logo_bbox"] is None:
        raise SystemExit("template has no logo_bbox")
    if not tpl["offsets"]:
        raise SystemExit("no button_offsets; run compute_logo_offsets.py first")

    frame = cv2.imread(args.frame)
    if frame is None:
        raise SystemExit(f"cannot read frame: {args.frame}")
    tpl_image_path = ROOT / tpl["image_url"]
    template_img = cv2.imread(str(tpl_image_path))
    if template_img is None:
        raise SystemExit(f"cannot read template image: {tpl_image_path}")

    lb = tpl["logo_bbox"]
    x, y, w, h = int(lb["x"]), int(lb["y"]), int(lb["width"]), int(lb["height"])
    logo_crop = template_img[y : y + h, x : x + w]

    pose = detect_logo(frame, logo_crop)
    result = match_with_logo_anchor(
        frame_points=frame,
        template_points=template_img,
        buttons=tpl["buttons"],
        logo_offsets=tpl["offsets"],
        logo_pose=pose,
        template_logo_width=float(lb["width"]),
        template_logo_center=(lb["x"] + lb["width"] / 2.0, lb["y"] + lb["height"] / 2.0),
    )

    print(f"tier: {result['tier']}")
    print(f"logo_pose: {result['logo_pose']}")
    print(
        "homography: inliers={} ratio={} reproj={}".format(
            result.get("inlier_count"),
            result.get("inlier_ratio"),
            result.get("reprojection_error"),
        )
    )

    vis = frame.copy()
    if pose is not None:
        lw2, lh2 = w * pose.scale / 2, h * pose.scale / 2
        cv2.rectangle(
            vis,
            (int(pose.center_x - lw2), int(pose.center_y - lh2)),
            (int(pose.center_x + lw2), int(pose.center_y + lh2)),
            (0, 0, 255),
            3,
        )
    for corners in result["coarse_buttons"].values():
        draw_quad(vis, corners, (0, 220, 255), thickness=1, dashed=True)
    final_color = (0, 200, 0) if result["tier"] == "HOMOGRAPHY_REFINED" else (0, 140, 255)
    for corners in result["projected_buttons"].values():
        draw_quad(vis, corners, final_color)
    cv2.imwrite(args.out, vis)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
