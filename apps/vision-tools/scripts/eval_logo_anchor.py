"""Synthetic evaluation harness for the logo-anchor vision pipeline.

Method (ground truth is free by construction):
  1. Each DB template that has a real photo is warped into a synthetic
     "camera frame" by a KNOWN transform M (similarity + optional
     perspective), then degraded photometrically (blur / brightness /
     noise / JPEG / logo occlusion).
  2. Because M is known, ground truth costs nothing: the GT logo center,
     GT logo width and GT button quads are simply the M-projection of the
     annotations already stored in the DB.
  3. The full runtime pipeline (detect_logo -> match_with_logo_anchor)
     runs on every frame and is scored against that ground truth.

Metrics per case:
  logo_detected          detect_logo returned a pose
  logo_err_px / _norm    pose center vs GT center (norm = err / GT logo width)
  tier                   HOMOGRAPHY_REFINED | LOGO_SIMILARITY | REJECTED
  button_hit_rate        fraction of buttons whose predicted center lies
                         inside the GT quad (primary usability metric)
  button_center_err_px   mean predicted-vs-GT button center distance
  button_iou             mean rasterized IoU of predicted vs GT quads
  runtime_s              end-to-end pipeline wall time

Negative controls: frames that do NOT contain the template (another
template's panel, pure noise, a flat gradient). Any returned pose is a
false accept.

Usage:
    PYTHONPATH=apps/vision-tools python apps/vision-tools/scripts/eval_logo_anchor.py \
        [--db apps/api/silvertech.sqlite3] [--out data/eval/vision] [--quick]
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None

from scripts.logo_anchor_match import detect_logo, match_with_logo_anchor
from scripts.run_logo_anchor import draw_quad, load_template

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = ROOT / "apps" / "api" / "silvertech.sqlite3"
DEFAULT_OUT = ROOT / "data" / "eval" / "vision"

FRAME_W, FRAME_H = 1600, 1200
BACKGROUND = 96  # flat mid-gray backdrop behind the warped panel

# Sweep levels (one factor at a time from the baseline pose).
BASELINE_REL_SCALE = 0.85
SCALE_LEVELS = [0.35, 0.5, 0.7, 0.85, 1.0]
ROTATION_LEVELS = [-15, -10, -5, 5, 10, 15]
PERSPECTIVE_LEVELS = [10, 20, 30]  # rotation about vertical axis, degrees
BLUR_LEVELS = [3, 5, 9, 13]  # Gaussian kernel size
BRIGHTNESS_LEVELS = [-60, -30, 30, 60]
NOISE_LEVELS = [5, 10, 20]  # Gaussian sigma
JPEG_LEVELS = [60, 40, 20]  # encode quality
OCCLUSION_LEVELS = [0.25, 0.5, 1.0]  # fraction of logo covered


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------

def build_transform(
    tpl_shape: tuple[int, ...],
    *,
    rel_scale: float = BASELINE_REL_SCALE,
    rot_deg: float = 0.0,
    persp_y_deg: float = 0.0,
    persp_x_deg: float = 0.0,
) -> np.ndarray:
    """3x3 template->frame matrix: in-plane rotation, out-of-plane tilt
    (K R K^-1 about the template center), then a similarity that fits the
    warped panel into the frame at rel_scale of the max fitting size."""
    th, tw = tpl_shape[:2]
    cx, cy = tw / 2.0, th / 2.0

    a = np.deg2rad(rot_deg)
    c, s = float(np.cos(a)), float(np.sin(a))
    rot = np.array(
        [[c, -s, cx - c * cx + s * cy], [s, c, cy - s * cx - c * cy], [0, 0, 1]]
    )

    f = float(max(tw, th))
    k = np.array([[f, 0, cx], [0, f, cy], [0, 0, 1]])
    ay, ax = np.deg2rad(persp_y_deg), np.deg2rad(persp_x_deg)
    ry = np.array(
        [[np.cos(ay), 0, np.sin(ay)], [0, 1, 0], [-np.sin(ay), 0, np.cos(ay)]]
    )
    rx = np.array(
        [[1, 0, 0], [0, np.cos(ax), -np.sin(ax)], [0, np.sin(ax), np.cos(ax)]]
    )
    persp = k @ (ry @ rx) @ np.linalg.inv(k)

    m0 = persp @ rot
    corners = np.float32([[0, 0], [tw, 0], [tw, th], [0, th]])
    warped = project_points(m0, corners)
    x0, y0 = warped.min(axis=0)
    x1, y1 = warped.max(axis=0)
    fit = min(FRAME_W / (x1 - x0), FRAME_H / (y1 - y0)) * rel_scale
    tx = FRAME_W / 2.0 - fit * (x0 + x1) / 2.0
    ty = FRAME_H / 2.0 - fit * (y0 + y1) / 2.0
    sim = np.array([[fit, 0, tx], [0, fit, ty], [0, 0, 1]])
    return sim @ m0


def project_points(m: np.ndarray, pts: np.ndarray) -> np.ndarray:
    pts = np.asarray(pts, dtype=np.float64).reshape(-1, 2)
    return cv2.perspectiveTransform(pts.reshape(-1, 1, 2), m).reshape(-1, 2)


def bbox_corners(bb: dict[str, float]) -> np.ndarray:
    x, y, w, h = bb["x"], bb["y"], bb["width"], bb["height"]
    return np.float64([[x, y], [x + w, y], [x + w, y + h], [x, y + h]])


# --------------------------------------------------------------------------
# Frame synthesis
# --------------------------------------------------------------------------

def render_frame(template_img: np.ndarray, m: np.ndarray) -> np.ndarray:
    return cv2.warpPerspective(
        template_img,
        m,
        (FRAME_W, FRAME_H),
        flags=cv2.INTER_AREA,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(BACKGROUND, BACKGROUND, BACKGROUND),
    )


def degrade(
    frame: np.ndarray,
    *,
    blur: int = 0,
    brightness: int = 0,
    noise: float = 0.0,
    jpeg: int = 0,
) -> np.ndarray:
    out = frame
    if blur:
        out = cv2.GaussianBlur(out, (blur, blur), 0)
    if brightness:
        out = cv2.convertScaleAbs(out, alpha=1.0, beta=brightness)
    if noise:
        rng = np.random.default_rng(42)
        out = np.clip(
            out.astype(np.float32) + rng.normal(0, noise, out.shape), 0, 255
        ).astype(np.uint8)
    if jpeg:
        _, buf = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, jpeg])
        out = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    return out


def occlude_logo(frame: np.ndarray, gt_logo_quad: np.ndarray, fraction: float) -> np.ndarray:
    """Cover the left `fraction` of the GT logo area with backdrop gray."""
    out = frame.copy()
    x0, y0 = gt_logo_quad.min(axis=0)
    x1, y1 = gt_logo_quad.max(axis=0)
    cover_x1 = x0 + (x1 - x0) * fraction
    cv2.rectangle(
        out,
        (int(x0), int(y0)),
        (int(cover_x1), int(y1)),
        (BACKGROUND, BACKGROUND, BACKGROUND),
        -1,
    )
    return out


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------

def quad_iou(pred: np.ndarray, gt: np.ndarray) -> float:
    pts = np.vstack([pred, gt])
    x0, y0 = np.floor(pts.min(axis=0)).astype(int)
    x1, y1 = np.ceil(pts.max(axis=0)).astype(int)
    w, h = max(1, x1 - x0), max(1, y1 - y0)
    mask_p = np.zeros((h, w), np.uint8)
    mask_g = np.zeros((h, w), np.uint8)
    cv2.fillPoly(mask_p, [np.round(pred - [x0, y0]).astype(np.int32)], 1)
    cv2.fillPoly(mask_g, [np.round(gt - [x0, y0]).astype(np.int32)], 1)
    inter = int(np.logical_and(mask_p, mask_g).sum())
    union = int(np.logical_or(mask_p, mask_g).sum())
    return inter / union if union else 0.0


def score_buttons(
    projected: dict[str, list[dict[str, float]]],
    gt_quads: dict[str, np.ndarray],
) -> dict[str, float]:
    hits, errors, ious = [], [], []
    for button_id, gt in gt_quads.items():
        quad = projected.get(button_id)
        if quad is None:
            hits.append(0.0)
            ious.append(0.0)
            continue
        pred = np.float64([[c["x"], c["y"]] for c in quad])
        pred_center = pred.mean(axis=0)
        gt_center = gt.mean(axis=0)
        inside = cv2.pointPolygonTest(gt.astype(np.float32), tuple(pred_center), False)
        hits.append(1.0 if inside >= 0 else 0.0)
        errors.append(float(np.hypot(*(pred_center - gt_center))))
        ious.append(quad_iou(pred, gt))
    return {
        "button_hit_rate": float(np.mean(hits)) if hits else 0.0,
        "button_center_err_px": float(np.mean(errors)) if errors else float("nan"),
        "button_iou": float(np.mean(ious)) if ious else 0.0,
    }


# --------------------------------------------------------------------------
# Case execution
# --------------------------------------------------------------------------

def run_case(
    *,
    template_id: str,
    template_img: np.ndarray,
    logo_crop: np.ndarray,
    tpl: dict,
    m: np.ndarray,
    frame: np.ndarray,
    sweep: str,
    level,
) -> dict:
    lb = tpl["logo_bbox"]
    gt_logo_quad = project_points(m, bbox_corners(lb))
    gt_center = gt_logo_quad.mean(axis=0)
    gt_logo_w = float(
        (
            np.linalg.norm(gt_logo_quad[1] - gt_logo_quad[0])
            + np.linalg.norm(gt_logo_quad[2] - gt_logo_quad[3])
        )
        / 2.0
    )
    gt_quads = {
        bid: project_points(m, bbox_corners(bb)) for bid, bb in tpl["buttons"].items()
    }

    t0 = time.perf_counter()
    stats: dict[str, float] = {}
    pose = detect_logo(frame, logo_crop, stats=stats)
    result = match_with_logo_anchor(
        frame_points=frame,
        template_points=template_img,
        buttons=tpl["buttons"],
        logo_offsets=tpl["offsets"],
        logo_pose=pose,
        template_logo_width=float(lb["width"]),
        template_logo_center=(lb["x"] + lb["width"] / 2.0, lb["y"] + lb["height"] / 2.0),
    )
    runtime = time.perf_counter() - t0

    logo_err = (
        float(np.hypot(pose.center_x - gt_center[0], pose.center_y - gt_center[1]))
        if pose is not None
        else float("nan")
    )
    row = {
        "template_id": template_id,
        "sweep": sweep,
        "level": level,
        "logo_detected": pose is not None,
        "logo_err_px": logo_err,
        "logo_err_norm": logo_err / gt_logo_w if pose is not None else float("nan"),
        "tier": result["tier"],
        "runtime_s": round(runtime, 3),
        "detect_stats": stats,
        **score_buttons(result["projected_buttons"], gt_quads),
    }
    row["_result"] = result
    row["_gt_quads"] = gt_quads
    return row


def make_cases(quick: bool) -> list[tuple[str, object, dict, dict]]:
    """(sweep, level, transform kwargs, degrade kwargs) — one factor at a time."""
    cases: list[tuple[str, object, dict, dict]] = [("baseline", 0, {}, {})]
    if quick:
        cases += [
            ("scale", 0.5, {"rel_scale": 0.5}, {}),
            ("rotation", 10, {"rot_deg": 10}, {}),
            ("blur", 9, {}, {"blur": 9}),
        ]
        return cases
    cases += [("scale", v, {"rel_scale": v}, {}) for v in SCALE_LEVELS if v != BASELINE_REL_SCALE]
    cases += [("rotation", v, {"rot_deg": v}, {}) for v in ROTATION_LEVELS]
    cases += [("perspective", v, {"persp_y_deg": v}, {}) for v in PERSPECTIVE_LEVELS]
    cases += [("perspective_x", 15, {"persp_x_deg": 15}, {})]
    cases += [("blur", v, {}, {"blur": v}) for v in BLUR_LEVELS]
    cases += [("brightness", v, {}, {"brightness": v}) for v in BRIGHTNESS_LEVELS]
    cases += [("noise", v, {}, {"noise": v}) for v in NOISE_LEVELS]
    cases += [("jpeg", v, {}, {"jpeg": v}) for v in JPEG_LEVELS]
    cases += [("occlusion", v, {}, {"_occlude": v}) for v in OCCLUSION_LEVELS]
    return cases


# --------------------------------------------------------------------------
# Negatives
# --------------------------------------------------------------------------

def negative_frames(other_panel: np.ndarray | None) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(7)
    frames = {
        "noise": rng.integers(0, 255, (FRAME_H, FRAME_W, 3), dtype=np.uint8),
        "gradient": np.tile(
            np.linspace(30, 220, FRAME_W, dtype=np.uint8), (FRAME_H, 1)
        )[..., None].repeat(3, axis=2),
    }
    if other_panel is not None:
        frames["other_panel"] = other_panel
    return frames


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------

PALETTE = ["#2a78d6", "#1baf7a", "#eda100", "#4a3aa7", "#e34948"]
SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT2 = "#52514e"


def style_axis(ax) -> None:
    ax.set_facecolor(SURFACE)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#d8d7d3")
    ax.tick_params(colors=TEXT2, labelsize=8)
    ax.grid(axis="y", color="#ecebe7", linewidth=0.8)
    ax.set_axisbelow(True)


def plot_sweeps(rows: list[dict], metric: str, ylabel: str, path: Path, ylim=None) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sweeps = [s for s in dict.fromkeys(r["sweep"] for r in rows) if s != "baseline"]
    templates = sorted({r["template_id"] for r in rows})
    ncols = 3
    nrows = -(-len(sweeps) // ncols)
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(11, 2.9 * nrows), facecolor=SURFACE, squeeze=False
    )
    baseline = {
        t: next(r[metric] for r in rows if r["template_id"] == t and r["sweep"] == "baseline")
        for t in templates
    }
    for idx, sweep in enumerate(sweeps):
        ax = axes[idx // ncols][idx % ncols]
        style_axis(ax)
        for t_idx, template in enumerate(templates):
            pts = [
                (r["level"], r[metric])
                for r in rows
                if r["template_id"] == template and r["sweep"] == sweep
            ]
            pts.sort(key=lambda p: p[0] if isinstance(p[0], (int, float)) else 0)
            xs = [str(p[0]) for p in pts]
            ys = [p[1] for p in pts]
            short = template.replace("template_", "").split("_")[0]
            ax.plot(
                xs, ys, marker="o", markersize=4, linewidth=2,
                color=PALETTE[t_idx], label=short,
            )
            ax.axhline(baseline[template], color=PALETTE[t_idx], linewidth=1, alpha=0.35)
        ax.set_title(sweep, fontsize=10, color=TEXT)
        if ylim:
            ax.set_ylim(*ylim)
        if idx % ncols == 0:
            ax.set_ylabel(ylabel, fontsize=8, color=TEXT2)
    for idx in range(len(sweeps), nrows * ncols):
        axes[idx // ncols][idx % ncols].axis("off")
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", fontsize=9, frameon=False)
    fig.suptitle(f"{ylabel} per perturbation sweep (thin line = baseline)", fontsize=11, color=TEXT)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def save_visual(frame: np.ndarray, row: dict, path: Path) -> None:
    vis = frame.copy()
    for gt in row["_gt_quads"].values():
        draw_quad(vis, [{"x": p[0], "y": p[1]} for p in gt], (214, 120, 42), thickness=2)
    color = (0, 200, 0) if row["tier"] == "HOMOGRAPHY_REFINED" else (0, 140, 255)
    for corners in row["_result"]["projected_buttons"].values():
        draw_quad(vis, corners, color, thickness=2)
    cv2.imwrite(str(path), vis)


def write_summary(out_dir: Path, rows: list[dict], negatives: list[dict]) -> None:
    def fmt(v: float) -> str:
        return "-" if v != v else f"{v:.3f}"  # NaN-safe

    lines = [
        "# Vision pipeline synthetic evaluation",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Method",
        "",
        "Template photos from the DB are warped into synthetic 1600x1200 camera",
        "frames by a KNOWN transform (scale / rotation / perspective) and degraded",
        "photometrically (blur / brightness / noise / JPEG / logo occlusion), one",
        "factor at a time from a frontal baseline. The known transform provides",
        "exact ground truth for the logo center and every button quad, so no manual",
        "labeling is needed. The full runtime pipeline (`detect_logo` ->",
        "`match_with_logo_anchor`) is scored against that ground truth.",
        "",
        "Primary metric: **button hit rate** — fraction of buttons whose predicted",
        "center falls inside the ground-truth button quad (a tap on the guided spot",
        "lands on the real button). Secondary: logo center error (in logo widths),",
        "mean button IoU, tier reached, runtime.",
        "",
        "## Per-case results",
        "",
        "| template | sweep | level | logo | logo err (norm) | tier | hit rate | IoU | center err px | runtime s |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        short = r["template_id"].replace("template_", "")
        lines.append(
            f"| {short} | {r['sweep']} | {r['level']} | "
            f"{'Y' if r['logo_detected'] else 'N'} | {fmt(r['logo_err_norm'])} | "
            f"{r['tier'].replace('HOMOGRAPHY_REFINED', 'HOMOG').replace('LOGO_SIMILARITY', 'LOGO')} | "
            f"{fmt(r['button_hit_rate'])} | {fmt(r['button_iou'])} | "
            f"{fmt(r['button_center_err_px'])} | {r['runtime_s']} |"
        )
    lines += ["", "## Aggregates", ""]
    for template in sorted({r["template_id"] for r in rows}):
        sub = [r for r in rows if r["template_id"] == template]
        det = np.mean([r["logo_detected"] for r in sub])
        hit = np.mean([r["button_hit_rate"] for r in sub])
        iou = np.mean([r["button_iou"] for r in sub])
        homog = np.mean([r["tier"] == "HOMOGRAPHY_REFINED" for r in sub])
        rt = np.mean([r["runtime_s"] for r in sub])
        lines.append(
            f"- **{template}**: logo detection {det:.0%}, mean hit rate {hit:.0%}, "
            f"mean IoU {iou:.2f}, homography tier {homog:.0%}, mean runtime {rt:.1f}s "
            f"({len(sub)} cases)"
        )
    lines += ["", "## Negative controls (false-accept check)", ""]
    lines.append("| logo from | frame | logo detected (false accept) | score |")
    lines.append("|---|---|---|---|")
    for n in negatives:
        lines.append(
            f"| {n['template_id'].replace('template_', '')} | {n['frame']} | "
            f"{'**YES**' if n['false_accept'] else 'no'} | {fmt(n['score'])} |"
        )
    fa = sum(n["false_accept"] for n in negatives)
    lines.append("")
    lines.append(f"False accepts: **{fa}/{len(negatives)}**")
    lines += [
        "",
        "## Files",
        "",
        "- `results.csv` / `results.json` — every case, machine-readable",
        "- `plots/hit_rate.png`, `plots/logo_err.png` — per-sweep curves",
        "- `visuals/` — annotated frames (orange = ground truth, green/amber = predicted)",
        "",
        "## Caveats",
        "",
        "- Synthetic warps of the SAME photo stored in the template: no lighting",
        "  change, no glare, no camera sensor noise beyond the modeled Gaussian.",
        "  Real handheld results are expected to be worse; treat these numbers as",
        "  an upper bound and a relative robustness profile.",
        "- Flat gray backdrop; cluttered backgrounds are not modeled here.",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines))


CSV_FIELDS = [
    "template_id", "sweep", "level", "logo_detected", "logo_err_px", "logo_err_norm",
    "tier", "button_hit_rate", "button_iou", "button_center_err_px", "runtime_s",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--quick", action="store_true", help="4 cases per template")
    args = parser.parse_args()
    if cv2 is None:
        raise SystemExit("OpenCV required: run inside the silvertech conda env")

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    template_ids = [
        r["id"]
        for r in conn.execute("SELECT id, template_image_url FROM templates")
        if not r["template_image_url"].endswith(".txt")
    ]
    templates = {}
    for tid in template_ids:
        tpl = load_template(conn, tid)
        img = cv2.imread(str(ROOT / tpl["image_url"]))
        if img is None or tpl["logo_bbox"] is None or not tpl["offsets"]:
            print(f"skip {tid}: missing image/logo_bbox/offsets")
            continue
        templates[tid] = (tpl, img)
    conn.close()
    if not templates:
        raise SystemExit("no usable templates (need real image + logo_bbox + offsets)")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out) / stamp
    (out_dir / "plots").mkdir(parents=True, exist_ok=True)
    (out_dir / "visuals").mkdir(exist_ok=True)

    rows: list[dict] = []
    cases = make_cases(args.quick)
    for tid, (tpl, img) in templates.items():
        lb = tpl["logo_bbox"]
        x, y, w, h = int(lb["x"]), int(lb["y"]), int(lb["width"]), int(lb["height"])
        logo_crop = img[y : y + h, x : x + w]
        for sweep, level, tkw, dkw in cases:
            m = build_transform(img.shape, **tkw)
            frame = render_frame(img, m)
            occlude = dkw.pop("_occlude", None)
            if occlude is not None:
                frame = occlude_logo(frame, project_points(m, bbox_corners(lb)), occlude)
            frame = degrade(frame, **dkw)
            if occlude is not None:
                dkw["_occlude"] = occlude  # restore, dict shared across templates
            row = run_case(
                template_id=tid, template_img=img, logo_crop=logo_crop, tpl=tpl,
                m=m, frame=frame, sweep=sweep, level=level,
            )
            rows.append(row)
            print(
                f"{tid} {sweep}={level}: logo={row['logo_detected']} "
                f"tier={row['tier']} hit={row['button_hit_rate']:.2f} "
                f"t={row['runtime_s']}s",
                flush=True,
            )
            if sweep in ("baseline", "perspective") and (
                sweep == "baseline" or level == PERSPECTIVE_LEVELS[-1]
            ):
                save_visual(frame, row, out_dir / "visuals" / f"{tid}_{sweep}_{level}.png")

    # Negatives: this template's logo vs frames that don't contain it.
    negatives: list[dict] = []
    tids = list(templates)
    for i, tid in enumerate(tids):
        tpl, img = templates[tid]
        lb = tpl["logo_bbox"]
        x, y, w, h = int(lb["x"]), int(lb["y"]), int(lb["width"]), int(lb["height"])
        logo_crop = img[y : y + h, x : x + w]
        other = None
        if len(tids) > 1:
            _, other_img = templates[tids[(i + 1) % len(tids)]]
            other = render_frame(other_img, build_transform(other_img.shape))
        for name, frame in negative_frames(other).items():
            stats: dict[str, float] = {}
            pose = detect_logo(frame, logo_crop, stats=stats)
            negatives.append(
                {
                    "template_id": tid,
                    "frame": name,
                    "false_accept": pose is not None,
                    "score": float(pose.score) if pose else stats.get("best_refined", stats.get("best_corr", 0.0)),
                }
            )
            print(f"negative {tid} vs {name}: false_accept={pose is not None}", flush=True)

    # Persist
    clean = [{k: r[k] for k in CSV_FIELDS} | {"detect_stats": r["detect_stats"]} for r in rows]
    (out_dir / "results.json").write_text(
        json.dumps({"cases": clean, "negatives": negatives}, indent=2)
    )
    with (out_dir / "results.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows([{k: r[k] for k in CSV_FIELDS} for r in rows])
    plot_sweeps(
        rows, "button_hit_rate", "button hit rate", out_dir / "plots" / "hit_rate.png",
        ylim=(-0.05, 1.05),
    )
    plot_sweeps(rows, "logo_err_norm", "logo center error (logo widths)", out_dir / "plots" / "logo_err.png")
    write_summary(out_dir, rows, negatives)
    print(f"\nwrote {out_dir}")


if __name__ == "__main__":
    main()
