"""Logo-anchored matching: detect the brand logo in a frame, project buttons
from stored logo-relative offsets, then refine with the ORB->homography pipeline.

Confidence tiers:
  HOMOGRAPHY_REFINED  homography passed the confidence gate (best)
  LOGO_SIMILARITY     logo found, similarity-only projection (coarse)
  REJECTED            logo not found and homography failed
"""

from __future__ import annotations

from typing import Any

import numpy as np

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover - environment dependent
    cv2 = None

from scripts.logo_anchor import LogoPose, project_offsets
from scripts.offline_match import match_and_project
from scripts.project_buttons import project_buttons

TIER_HOMOGRAPHY = "HOMOGRAPHY_REFINED"
TIER_LOGO = "LOGO_SIMILARITY"
TIER_REJECTED = "REJECTED"

MIN_LOGO_SCORE = 0.55
LOGO_PYRAMID_SCALES = np.linspace(0.1, 1.6, 31)
LOGO_FINE_FACTORS = np.linspace(0.85, 1.15, 13)

# Candidate verification: raw-grayscale matchTemplate alone false-positives on
# any bright-text-on-dark patch (gloss, unrelated labels), and tiny pyramid
# scales match high-frequency text everywhere. Score coarse peaks on a blend
# of edge-map and grayscale correlation, keep the top K across scales, then
# re-rank by correlating each candidate window against the logo at a fixed
# canonical resolution (scale-normalized, so tiny false peaks lose).
LOGO_EDGE_WEIGHT = 0.6
LOGO_TOP_K = 5
LOGO_CANON_WIDTH = 200
LOGO_VERIFY_PAD = 0.35
# SIFT good matches (ratio test) between logo and candidate window at
# canonical resolution. Real logo: tens of matches; unrelated text: <6.
LOGO_SIFT_MIN_MATCHES = 10
LOGO_SIFT_RATIO = 0.75
# Soft accept: neither signal alone clears its strict gate, but moderate SIFT
# evidence (above the <6 unrelated-text band) combined with a solid refined
# correlation is far from any measured false positive (noise refined=0.12,
# false peak corr=0.593). Real handheld photos land here (sift=7 refined=0.74).
LOGO_SIFT_SOFT_MATCHES = 6
LOGO_SOFT_MIN_REFINED = 0.65
# Coarse pyramid search runs on a frame downscaled to this max dimension
# (5k-px photos take ~35s at full res); SIFT verification and refinement
# still use the full-resolution frame, so accuracy is unaffected.
LOGO_SEARCH_MAX_DIM = 1600

# Real photos: ORB finds hundreds of keypoints on a 5k-px image but glossy
# panels yield few good matches, so inliers/total_keypoints is meaningless.
# Gate on absolute inlier count + reprojection error instead.
REAL_MIN_INLIERS = 15
REAL_MIN_INLIER_RATIO = 0.0
REAL_MAX_REPROJ = 5.0

# Per-button local refinement (matchTemplate snap around predicted position)
LOCAL_SNAP_MIN_SCORE = 0.45
LOCAL_SEARCH_MARGIN = 0.6  # search window padding as fraction of button size

# Homography sanity: projected logo center must land within this many
# detected-logo-widths of where the logo detector found it. A few clustered
# inliers can pass the count/reproj gate yet produce a wildly wrong transform.
LOGO_CONSISTENCY_MAX_DIST = 1.5

# SIFT global homography fallback (ORB struggles on glossy low-contrast
# panels; SIFT usually still finds enough structure). Matching runs on
# downscaled images, the matrix is re-expressed in full-resolution coords.
SIFT_HOMOG_MAX_DIM = 1600
SIFT_HOMOG_RATIO = 0.75
SIFT_HOMOG_MIN_INLIERS = 12

# Snap-then-fit: buttons whose local matchTemplate snap is confident become
# template->frame correspondences; a homography fitted through them models
# perspective that the similarity projection cannot.
SNAP_FIT_MIN_SCORE = 0.55
SNAP_FIT_MIN_BUTTONS = 5

# Homography extrapolation sanity: inliers clustered on one small patch (e.g.
# just the logo) can pass every count/reproj/logo gate yet project buttons
# 1000+px off, because the transform is only constrained locally. Require the
# inlier convex hull to cover a minimum fraction of the projected button area.
INLIER_SPREAD_MIN_RATIO = 0.05

# Projected button areas must agree with the logo-derived scale. Near-collinear
# matches can fit a homography with sub-px reprojection that still collapses
# (or explodes) the far-away button region; perspective legitimately varies
# area across the panel, so the band is wide.
BUTTON_AREA_RATIO_MIN = 0.02
BUTTON_AREA_RATIO_MAX = 50.0


def _is_image(arr: np.ndarray) -> bool:
    return arr.ndim == 3 or (arr.ndim == 2 and arr.shape[1] != 2)


def _edge_map(gray: np.ndarray) -> np.ndarray:
    edges = cv2.Canny(gray, 50, 150)
    # Dilate so slightly misaligned edges still overlap during correlation.
    return cv2.dilate(edges, np.ones((3, 3), np.uint8))


def _canonical_verify(
    frame_gray: np.ndarray,
    logo_canon: np.ndarray,
    logo_size: tuple[int, int],
    cx: float,
    cy: float,
    scale: float,
) -> tuple[float, float, float] | None:
    """Correlate a candidate window against the logo at canonical resolution.

    Upscales the window so the hypothesized logo matches logo_canon's size,
    then matchTemplates within it. Returns (score, refined_cx, refined_cy).
    """
    lw, lh = logo_size
    w, h = lw * scale, lh * scale
    pad = LOGO_VERIFY_PAD
    x0 = int(max(0, cx - w / 2 - w * pad))
    y0 = int(max(0, cy - h / 2 - h * pad))
    x1 = int(min(frame_gray.shape[1], cx + w / 2 + w * pad))
    y1 = int(min(frame_gray.shape[0], cy + h / 2 + h * pad))
    window = frame_gray[y0:y1, x0:x1]
    if window.size == 0 or w < 1:
        return None
    f = logo_canon.shape[1] / w
    window_c = cv2.resize(
        window,
        (max(1, int(window.shape[1] * f)), max(1, int(window.shape[0] * f))),
        interpolation=cv2.INTER_CUBIC,
    )
    if window_c.shape[0] < logo_canon.shape[0] or window_c.shape[1] < logo_canon.shape[1]:
        return None
    result = cv2.matchTemplate(window_c, logo_canon, cv2.TM_CCOEFF_NORMED)
    _, score, _, loc = cv2.minMaxLoc(result)
    refined_cx = x0 + (loc[0] + logo_canon.shape[1] / 2.0) / f
    refined_cy = y0 + (loc[1] + logo_canon.shape[0] / 2.0) / f
    return (float(score), refined_cx, refined_cy)


def _sift_match_count(
    frame_gray: np.ndarray,
    logo_canon: np.ndarray,
    logo_size: tuple[int, int],
    cx: float,
    cy: float,
    scale: float,
) -> int:
    """Count SIFT ratio-test matches between logo and candidate window,
    both at canonical resolution. Distinguishes the actual logo letterforms
    from unrelated bright-on-dark text that fools plain correlation."""
    lw, lh = logo_size
    w, h = lw * scale, lh * scale
    pad = LOGO_VERIFY_PAD
    x0 = int(max(0, cx - w / 2 - w * pad))
    y0 = int(max(0, cy - h / 2 - h * pad))
    x1 = int(min(frame_gray.shape[1], cx + w / 2 + w * pad))
    y1 = int(min(frame_gray.shape[0], cy + h / 2 + h * pad))
    window = frame_gray[y0:y1, x0:x1]
    if window.size == 0 or w < 1:
        return 0
    f = logo_canon.shape[1] / w
    window_c = cv2.resize(
        window,
        (max(1, int(window.shape[1] * f)), max(1, int(window.shape[0] * f))),
        interpolation=cv2.INTER_CUBIC,
    )
    sift = cv2.SIFT_create()
    _, desc_logo = sift.detectAndCompute(logo_canon, None)
    _, desc_win = sift.detectAndCompute(window_c, None)
    if desc_logo is None or desc_win is None or len(desc_win) < 2:
        return 0
    matches = cv2.BFMatcher().knnMatch(desc_logo, desc_win, k=2)
    return sum(1 for m, n in matches if m.distance < LOGO_SIFT_RATIO * n.distance)


def _gray(img: np.ndarray) -> np.ndarray:
    return img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def _sift_homography(
    template_img: np.ndarray,
    frame_img: np.ndarray,
    buttons: dict[str, dict[str, float]],
) -> dict[str, Any] | None:
    """Full template->frame homography from SIFT matches on downscaled images.

    Returns a match_and_project-shaped dict, or None when evidence is thin.
    """
    sift = cv2.SIFT_create()
    scaled = []
    for img in (template_img, frame_img):
        gray = _gray(img)
        s = 1.0
        max_dim = max(gray.shape[:2])
        if max_dim > SIFT_HOMOG_MAX_DIM:
            s = SIFT_HOMOG_MAX_DIM / max_dim
            gray = cv2.resize(gray, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        kp, desc = sift.detectAndCompute(gray, None)
        if desc is None or len(desc) < 2:
            return None
        scaled.append((kp, desc, s))
    (tpl_kp, tpl_desc, s_t), (frm_kp, frm_desc, s_f) = scaled

    pairs = cv2.BFMatcher().knnMatch(tpl_desc, frm_desc, k=2)
    good = [m for m, n in pairs if m.distance < SIFT_HOMOG_RATIO * n.distance]
    # Keep only the best match per frame keypoint: many-to-one clusters let
    # RANSAC fit degenerate transforms (same failure mode as brand_gallery).
    best_by_train: dict[int, Any] = {}
    for m in good:
        prev = best_by_train.get(m.trainIdx)
        if prev is None or m.distance < prev.distance:
            best_by_train[m.trainIdx] = m
    good = list(best_by_train.values())
    if len(good) < SIFT_HOMOG_MIN_INLIERS:
        return None

    src = np.float32([tpl_kp[m.queryIdx].pt for m in good]) / s_t
    dst = np.float32([frm_kp[m.trainIdx].pt for m in good]) / s_f
    matrix, mask = cv2.findHomography(src, dst, cv2.RANSAC, REAL_MAX_REPROJ)
    if matrix is None or mask is None:
        return None
    inlier_mask = mask.ravel().astype(bool)
    inliers = int(inlier_mask.sum())
    if inliers < SIFT_HOMOG_MIN_INLIERS:
        return None
    proj = cv2.perspectiveTransform(src[inlier_mask].reshape(-1, 1, 2), matrix).reshape(-1, 2)
    error = float(np.sqrt(np.mean(np.sum((proj - dst[inlier_mask]) ** 2, axis=1))))
    if error > REAL_MAX_REPROJ:
        return None
    return {
        "accepted": True,
        "failure_reason": None,
        "match_score": inliers / len(good),
        "inlier_count": inliers,
        "inlier_ratio": inliers / len(good),
        "reprojection_error": error,
        "matrix": matrix.tolist(),
        "inlier_frame_points": dst[inlier_mask].tolist(),
        "projected_buttons": project_buttons(buttons, np.asarray(matrix)),
    }


def _fit_homography_from_snaps(
    frame: np.ndarray,
    template_img: np.ndarray,
    buttons: dict[str, dict[str, float]],
    quads: dict[str, list[dict[str, float]]],
) -> dict[str, list[dict[str, float]]] | None:
    """Upgrade a similarity projection to a perspective one using confident
    per-button local snaps as template->frame correspondences."""
    snapped, scores = refine_buttons_local(frame, template_img, buttons, quads)
    good_ids = [b for b, s in scores.items() if s >= SNAP_FIT_MIN_SCORE and b in buttons]
    if len(good_ids) < SNAP_FIT_MIN_BUTTONS:
        return None
    src, dst = [], []
    for b in good_ids:
        bb = buttons[b]
        src.append([bb["x"] + bb["width"] / 2.0, bb["y"] + bb["height"] / 2.0])
        corners = snapped[b]
        dst.append([sum(c["x"] for c in corners) / 4.0, sum(c["y"] for c in corners) / 4.0])
    matrix, mask = cv2.findHomography(
        np.float32(src), np.float32(dst), cv2.RANSAC, REAL_MAX_REPROJ * 2
    )
    if matrix is None or mask is None or int(mask.sum()) < SNAP_FIT_MIN_BUTTONS:
        return None
    return project_buttons(buttons, np.asarray(matrix))


def detect_logo(
    frame: np.ndarray,
    logo_crop: np.ndarray,
    *,
    min_score: float = MIN_LOGO_SCORE,
    stats: dict[str, float] | None = None,
) -> LogoPose | None:
    """Multi-scale logo detection: edge+grayscale template matching for
    candidates, ORB feature verification to reject false peaks.

    Returns the best pose or None when confidence is below min_score.
    Rotation is assumed near-zero (frontal camera); the homography refine
    step handles rotated/perspective cases.

    When stats is given it is filled with best_corr / best_sift / best_refined
    for the strongest candidate, even on failure (diagnostics for callers).
    """
    if cv2 is None:
        return None
    frame_gray = frame if frame.ndim == 2 else cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    logo_gray = logo_crop if logo_crop.ndim == 2 else cv2.cvtColor(logo_crop, cv2.COLOR_BGR2GRAY)
    lh, lw = logo_gray.shape[:2]

    # Coarse search on a downscaled frame; centers map back via 1/down.
    down = 1.0
    max_dim = max(frame_gray.shape[:2])
    if max_dim > LOGO_SEARCH_MAX_DIM:
        down = LOGO_SEARCH_MAX_DIM / max_dim
        search_gray = cv2.resize(frame_gray, None, fx=down, fy=down, interpolation=cv2.INTER_AREA)
    else:
        search_gray = frame_gray
    search_edges = _edge_map(search_gray)

    def match_at(scale: float) -> tuple[float, float, float, float] | None:
        w, h = int(lw * scale * down), int(lh * scale * down)
        if w < 12 or h < 8 or w > search_gray.shape[1] or h > search_gray.shape[0]:
            return None
        resized = cv2.resize(logo_gray, (w, h), interpolation=cv2.INTER_AREA)
        res_gray = cv2.matchTemplate(search_gray, resized, cv2.TM_CCOEFF_NORMED)
        res_edge = cv2.matchTemplate(search_edges, _edge_map(resized), cv2.TM_CCOEFF_NORMED)
        combined = LOGO_EDGE_WEIGHT * res_edge + (1.0 - LOGO_EDGE_WEIGHT) * res_gray
        _, score, _, loc = cv2.minMaxLoc(combined)
        return (
            float(score),
            (loc[0] + w / 2.0) / down,
            (loc[1] + h / 2.0) / down,
            float(scale),
        )

    candidates: list[tuple[float, float, float, float]] = []
    for scale in LOGO_PYRAMID_SCALES:
        hit = match_at(scale)
        if hit is not None:
            candidates.append(hit)
    candidates.sort(key=lambda c: c[0], reverse=True)
    # Deduplicate peaks that landed on the same spot at neighboring scales.
    top: list[tuple[float, float, float, float]] = []
    for cand in candidates:
        if len(top) >= LOGO_TOP_K:
            break
        if all(np.hypot(cand[1] - t[1], cand[2] - t[2]) > lw * cand[3] * 0.5 for t in top):
            top.append(cand)
    if stats is not None:
        stats["best_corr"] = top[0][0] if top else 0.0
    if not top:
        return None

    canon_w = LOGO_CANON_WIDTH
    canon_h = max(8, int(canon_w * lh / lw))
    logo_canon = cv2.resize(logo_gray, (canon_w, canon_h), interpolation=cv2.INTER_AREA)

    # Re-rank: SIFT feature evidence picks the winner (letterforms, not just
    # bright-text-on-dark layout); fall back to correlation gated by min_score.
    sift_counts = [
        _sift_match_count(frame_gray, logo_canon, (lw, lh), c[1], c[2], c[3]) for c in top
    ]
    order = sorted(range(len(top)), key=lambda i: sift_counts[i], reverse=True)
    best_sift = sift_counts[order[0]]
    if stats is not None:
        stats["best_sift"] = float(best_sift)
    chosen = top[order[0]] if best_sift >= LOGO_SIFT_MIN_MATCHES else None

    # Refine center + scale via canonical-resolution correlation.
    def refine(cand: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
        best = None  # (corr, cx, cy, scale)
        _, cx, cy, scale = cand
        for factor in LOGO_FINE_FACTORS:
            hit = _canonical_verify(frame_gray, logo_canon, (lw, lh), cx, cy, scale * factor)
            if hit is not None and (best is None or hit[0] > best[0]):
                best = (hit[0], hit[1], hit[2], scale * factor)
        return best if best is not None else (cand[0], cx, cy, scale)

    if chosen is not None:
        score, cx, cy, scale = refine(chosen)
        return LogoPose(
            center_x=float(cx), center_y=float(cy), scale=float(scale),
            rotation=0.0, score=float(score),
        )

    # Soft accept: moderate SIFT evidence + solid refined correlation agree.
    if best_sift >= LOGO_SIFT_SOFT_MATCHES:
        score, cx, cy, scale = refine(top[order[0]])
        if stats is not None:
            stats["best_refined"] = float(score)
        if score >= LOGO_SOFT_MIN_REFINED:
            return LogoPose(
                center_x=float(cx), center_y=float(cy), scale=float(scale),
                rotation=0.0, score=float(score),
            )

    # No feature evidence anywhere: only trust a near-perfect correlation
    # (0.593 was measured on a false peak, so min_score alone is not enough).
    refined = [refine(c) for c in top]
    score, cx, cy, scale = max(refined, key=lambda r: r[0])
    if stats is not None:
        stats["best_refined"] = float(score)
    if score < max(min_score, 0.75):
        return None
    return LogoPose(
        center_x=float(cx), center_y=float(cy), scale=float(scale),
        rotation=0.0, score=float(score),
    )


def match_with_logo_anchor(
    *,
    frame_points: np.ndarray,
    template_points: np.ndarray,
    buttons: dict[str, dict[str, float]],
    logo_offsets: dict[str, dict[str, float]],
    logo_pose: LogoPose | None,
    template_logo_width: float,
    template_logo_center: tuple[float, float] | None = None,
) -> dict[str, Any]:
    """
    Perform template matching by aligning keypoints and checking geometric constraints.

    Combines coarse pose detection (via brand logo alignment) with fine-grained
    ORB feature matching and Homography estimation. Validates geometric safety gates:
    reprojection error, logo consistency, inlier spatial spread, and projected
    button area scales.

    Args:
        frame_points (np.ndarray): Target frame image, or synthetic keypoint coordinates.
        template_points (np.ndarray): Template image, or synthetic keypoint coordinates.
        buttons (dict[str, dict[str, float]]): Bounding boxes of buttons in template coords.
        logo_offsets (dict[str, dict[str, float]]): Offset coordinates of buttons relative to logo.
        logo_pose (LogoPose | None): Coarse logo pose returned by logo detection.
        template_logo_width (float): Physical or pixel width of the logo in the template.
        template_logo_center (tuple[float, float] | None): Center coordinates of logo in template.

    Returns:
        dict[str, Any]: A dictionary containing the matching outcome, confidence metrics,
            and the projected button coordinates.
    """
    coarse: dict[str, list[dict[str, float]]] = {}
    if logo_pose is not None and logo_offsets:
        coarse = project_offsets(logo_offsets, logo_pose, template_logo_width)

    real_images = _is_image(np.asarray(frame_points)) and _is_image(np.asarray(template_points))
    if real_images:
        refined = match_and_project(
            template_points,
            frame_points,
            buttons,
            min_inliers=REAL_MIN_INLIERS,
            min_inlier_ratio=REAL_MIN_INLIER_RATIO,
            max_reprojection_error=REAL_MAX_REPROJ,
        )
    else:
        refined = match_and_project(template_points, frame_points, buttons)

    def check_logo_consistency(result: dict[str, Any]) -> dict[str, Any]:
        if (
            not result["accepted"]
            or logo_pose is None
            or template_logo_center is None
            or result.get("matrix") is None
        ):
            return result
        h = np.asarray(result["matrix"])
        cx, cy, w_ = np.array([*template_logo_center, 1.0]) @ h.T
        if abs(w_) < 1e-9:
            return {**result, "accepted": False, "failure_reason": "degenerate_homography"}
        dist = np.hypot(cx / w_ - logo_pose.center_x, cy / w_ - logo_pose.center_y)
        limit = LOGO_CONSISTENCY_MAX_DIST * logo_pose.scale * template_logo_width
        if dist > limit:
            return {
                **result,
                "accepted": False,
                "failure_reason": "homography_inconsistent_with_logo",
            }
        return result

    def check_inlier_spread(result: dict[str, Any]) -> dict[str, Any]:
        if not result["accepted"] or not real_images:
            return result
        pts = result.get("inlier_frame_points")
        proj = result.get("projected_buttons")
        if not pts or not proj:
            return result
        pts = np.float32(pts)
        if len(pts) < 3:
            return {**result, "accepted": False, "failure_reason": "inliers_not_spread"}
        inlier_area = cv2.contourArea(cv2.convexHull(pts))
        corners = np.float32([[c["x"], c["y"]] for quad in proj.values() for c in quad])
        button_area = cv2.contourArea(cv2.convexHull(corners))
        if button_area > 0 and inlier_area < INLIER_SPREAD_MIN_RATIO * button_area:
            return {**result, "accepted": False, "failure_reason": "inliers_not_spread"}
        return result

    def check_button_scale(result: dict[str, Any]) -> dict[str, Any]:
        if not result["accepted"] or logo_pose is None or not result.get("projected_buttons"):
            return result
        scale2 = (logo_pose.scale) ** 2
        ratios = []
        for button_id, quad in result["projected_buttons"].items():
            bb = buttons.get(button_id)
            if bb is None or bb["width"] * bb["height"] <= 0:
                continue
            xs = [c["x"] for c in quad]
            ys = [c["y"] for c in quad]
            # Shoelace area of the projected quad.
            area = 0.5 * abs(
                sum(xs[i] * ys[(i + 1) % 4] - xs[(i + 1) % 4] * ys[i] for i in range(4))
            )
            ratios.append(area / (bb["width"] * bb["height"] * scale2))
        if not ratios:
            return result
        median = float(np.median(ratios))
        if median < BUTTON_AREA_RATIO_MIN or median > BUTTON_AREA_RATIO_MAX:
            return {**result, "accepted": False, "failure_reason": "button_scale_implausible"}
        return result

    refined = check_button_scale(check_inlier_spread(check_logo_consistency(refined)))

    # ORB failed: try SIFT global homography (better on glossy panels).
    if not refined["accepted"] and real_images:
        sift_refined = _sift_homography(template_points, frame_points, buttons)
        if sift_refined is not None:
            sift_refined = check_button_scale(
                check_inlier_spread(check_logo_consistency(sift_refined))
            )
            if sift_refined["accepted"]:
                refined = sift_refined

    def finish(result: dict[str, Any]) -> dict[str, Any]:
        if real_images and result["projected_buttons"]:
            snapped, scores = refine_buttons_local(
                np.asarray(frame_points),
                np.asarray(template_points),
                buttons,
                result["projected_buttons"],
            )
            result["projected_buttons"] = snapped
            result["local_scores"] = scores
        else:
            result["local_scores"] = {}
        return result

    if refined["accepted"]:
        return finish({
            "tier": TIER_HOMOGRAPHY,
            "accepted": True,
            "failure_reason": None,
            "logo_pose": _pose_dict(logo_pose),
            "coarse_buttons": coarse,
            "projected_buttons": refined["projected_buttons"],
            "match_score": refined.get("match_score"),
            "inlier_count": refined.get("inlier_count"),
            "inlier_ratio": refined.get("inlier_ratio"),
            "reprojection_error": refined.get("reprojection_error"),
        })
    if coarse:
        # Similarity projection can't model out-of-plane tilt; if enough
        # buttons snap confidently, refit their centers as a homography.
        fitted = None
        if real_images:
            fitted = _fit_homography_from_snaps(
                np.asarray(frame_points), np.asarray(template_points), buttons, coarse
            )
        return finish({
            "tier": TIER_LOGO,
            "accepted": True,
            "failure_reason": None,
            "logo_pose": _pose_dict(logo_pose),
            "coarse_buttons": coarse,
            "projected_buttons": fitted if fitted is not None else coarse,
            "perspective_fit": fitted is not None,
            "match_score": logo_pose.score if logo_pose else None,
            "inlier_count": refined.get("inlier_count"),
            "inlier_ratio": refined.get("inlier_ratio"),
            "reprojection_error": refined.get("reprojection_error"),
        })
    return {
        "tier": TIER_REJECTED,
        "local_scores": {},
        "accepted": False,
        "failure_reason": refined.get("failure_reason") or "logo_not_found",
        "logo_pose": None,
        "coarse_buttons": {},
        "projected_buttons": {},
        "match_score": refined.get("match_score"),
        "inlier_count": refined.get("inlier_count"),
        "inlier_ratio": refined.get("inlier_ratio"),
        "reprojection_error": refined.get("reprojection_error"),
    }


def refine_buttons_local(
    frame: np.ndarray,
    template_img: np.ndarray,
    buttons: dict[str, dict[str, float]],
    quads: dict[str, list[dict[str, float]]],
    *,
    min_score: float = LOCAL_SNAP_MIN_SCORE,
    margin: float = LOCAL_SEARCH_MARGIN,
) -> tuple[dict[str, list[dict[str, float]]], dict[str, float]]:
    """Snap each projected button to the best local matchTemplate hit.

    For every button, the template crop is resized to the projected size and
    searched in a window around the predicted position; when the match score
    clears min_score the whole quad is shifted to the found center. Corrects
    residual drift from imperfect scale/perspective without moving buttons
    that have no local evidence.
    """
    if cv2 is None:
        return quads, {}
    frame_gray = frame if frame.ndim == 2 else cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    tpl_gray = (
        template_img if template_img.ndim == 2 else cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
    )
    fh, fw = frame_gray.shape[:2]
    snapped: dict[str, list[dict[str, float]]] = {}
    scores: dict[str, float] = {}
    for button_id, corners in quads.items():
        bb = buttons.get(button_id)
        if bb is None:
            snapped[button_id] = corners
            continue
        xs = [c["x"] for c in corners]
        ys = [c["y"] for c in corners]
        qw, qh = max(xs) - min(xs), max(ys) - min(ys)
        cx, cy = sum(xs) / 4.0, sum(ys) / 4.0
        if qw < 6 or qh < 6:
            snapped[button_id] = corners
            continue
        crop = tpl_gray[
            int(bb["y"]) : int(bb["y"] + bb["height"]),
            int(bb["x"]) : int(bb["x"] + bb["width"]),
        ]
        if crop.size == 0:
            snapped[button_id] = corners
            continue
        resized = cv2.resize(crop, (max(int(qw), 4), max(int(qh), 4)), interpolation=cv2.INTER_AREA)
        x0 = int(max(0, cx - qw / 2 - qw * margin))
        y0 = int(max(0, cy - qh / 2 - qh * margin))
        x1 = int(min(fw, cx + qw / 2 + qw * margin))
        y1 = int(min(fh, cy + qh / 2 + qh * margin))
        window = frame_gray[y0:y1, x0:x1]
        if window.shape[0] < resized.shape[0] or window.shape[1] < resized.shape[1]:
            snapped[button_id] = corners
            continue
        result = cv2.matchTemplate(window, resized, cv2.TM_CCOEFF_NORMED)
        _, score, _, loc = cv2.minMaxLoc(result)
        scores[button_id] = float(score)
        if score < min_score:
            snapped[button_id] = corners
            continue
        new_cx = x0 + loc[0] + resized.shape[1] / 2.0
        new_cy = y0 + loc[1] + resized.shape[0] / 2.0
        dx, dy = new_cx - cx, new_cy - cy
        snapped[button_id] = [{"x": c["x"] + dx, "y": c["y"] + dy} for c in corners]
    return snapped, scores


def _pose_dict(pose: LogoPose | None) -> dict[str, float] | None:
    if pose is None:
        return None
    return {
        "center_x": pose.center_x,
        "center_y": pose.center_y,
        "scale": pose.scale,
        "rotation": pose.rotation,
        "score": pose.score,
    }
