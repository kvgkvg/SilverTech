"""Brand detection via SIFT gallery matching (Option A prototype).

One clean logo image per brand lives in data/brands/<brand>.png. A frame is
matched against every brand's SIFT descriptors; the winner needs an absolute
match count AND a margin over the runner-up, then estimateAffinePartial2D
turns the matched points into a LogoPose (center, scale, rotation).

Usage:
    python -m scripts.brand_gallery <frame.jpg> [--brands-dir data/brands]
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover - environment dependent
    cv2 = None

from scripts.logo_anchor import LogoPose

SIFT_RATIO = 0.75
MIN_MATCHES = 12          # absolute evidence for the winning brand
MIN_MARGIN = 1.5          # winner must have >= margin * runner-up matches
MIN_POSE_INLIERS = 8      # affine estimate needs this many RANSAC inliers
MIN_INLIER_RATIO = 0.4    # inliers/matches; unrelated text matches scatter
FRAME_MAX_DIM = 1600      # SIFT on a downscaled frame; pose maps back


@dataclass(frozen=True)
class BrandLogo:
    brand: str
    image: np.ndarray  # grayscale logo
    keypoints: tuple
    descriptors: np.ndarray | None


@dataclass(frozen=True)
class BrandMatch:
    brand: str
    match_count: int
    runner_up: str | None
    runner_up_count: int
    pose: LogoPose | None
    inliers: int


def _load_logo(path: Path) -> tuple[np.ndarray, np.ndarray | None]:
    """Read a gallery image as (grayscale, mask). A transparent PNG's alpha
    channel becomes the feature mask so background pixels contribute no
    keypoints; opaque images get no mask."""
    raw = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if raw is None:
        return None, None
    mask = None
    if raw.ndim == 3 and raw.shape[2] == 4:
        alpha = raw[:, :, 3]
        mask = (alpha > 0).astype(np.uint8) * 255
        # Dilate so keypoints on letter edges keep their support region.
        mask = cv2.dilate(mask, np.ones((5, 5), np.uint8))
        gray = cv2.cvtColor(raw[:, :, :3], cv2.COLOR_BGR2GRAY)
        # Flatten transparent pixels to the median logo intensity inverted,
        # giving edges contrast without inventing background texture.
        fill = 255 - int(np.median(gray[alpha > 0])) if (alpha > 0).any() else 255
        gray = np.where(alpha > 0, gray, fill).astype(np.uint8)
    elif raw.ndim == 3:
        gray = cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY)
    else:
        gray = raw
    return gray, mask


def load_gallery(brands_dir: Path) -> list[BrandLogo]:
    sift = cv2.SIFT_create()
    gallery: list[BrandLogo] = []
    for path in sorted(brands_dir.glob("*.png")) + sorted(brands_dir.glob("*.jpg")):
        img, mask = _load_logo(path)
        if img is None:
            continue
        kp, desc = sift.detectAndCompute(img, mask)
        gallery.append(BrandLogo(path.stem, img, tuple(kp), desc))
    return gallery


def _ratio_matches(desc_logo: np.ndarray, desc_frame: np.ndarray) -> list:
    matcher = cv2.BFMatcher()
    pairs = matcher.knnMatch(desc_logo, desc_frame, k=2)
    good = [m for m, n in pairs if m.distance < SIFT_RATIO * n.distance]
    # Many logo keypoints matching ONE frame keypoint is degenerate (a scale-0
    # similarity fits them all); keep only the best match per frame keypoint.
    best_by_train: dict[int, Any] = {}
    for m in good:
        prev = best_by_train.get(m.trainIdx)
        if prev is None or m.distance < prev.distance:
            best_by_train[m.trainIdx] = m
    return list(best_by_train.values())


def _pose_from_matches(
    logo: BrandLogo,
    frame_kp: tuple,
    matches: list,
    scale_back: float,
) -> tuple[LogoPose | None, int]:
    """Similarity transform logo->frame from matched keypoints; returns pose."""
    if len(matches) < MIN_POSE_INLIERS:
        return None, 0
    src = np.float32([logo.keypoints[m.queryIdx].pt for m in matches])
    dst = np.float32([frame_kp[m.trainIdx].pt for m in matches]) * scale_back
    matrix, inlier_mask = cv2.estimateAffinePartial2D(
        src, dst, method=cv2.RANSAC, ransacReprojThreshold=5.0
    )
    if matrix is None or inlier_mask is None:
        return None, 0
    inliers = int(inlier_mask.sum())
    if inliers < MIN_POSE_INLIERS:
        return None, inliers
    a, b = matrix[0, 0], matrix[1, 0]
    scale = float(np.hypot(a, b))
    rotation = float(np.arctan2(b, a))
    lh, lw = logo.image.shape[:2]
    # Scale sanity: a real logo occupies a visible chunk of the frame; a
    # near-zero or huge scale means RANSAC fit a degenerate point cluster.
    if lw * scale < 20 or scale > 20:
        return None, inliers
    center = matrix @ np.array([lw / 2.0, lh / 2.0, 1.0])
    return (
        LogoPose(
            center_x=float(center[0]),
            center_y=float(center[1]),
            scale=scale,
            rotation=rotation,
            score=min(1.0, inliers / max(len(matches), 1)),
        ),
        inliers,
    )


def detect_brand(frame: np.ndarray, gallery: list[BrandLogo]) -> BrandMatch | None:
    """Return the winning brand + logo pose, or None when ambiguous/absent."""
    frame_gray = frame if frame.ndim == 2 else cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    scale_back = 1.0
    max_dim = max(frame_gray.shape[:2])
    if max_dim > FRAME_MAX_DIM:
        f = FRAME_MAX_DIM / max_dim
        frame_gray = cv2.resize(frame_gray, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
        scale_back = 1.0 / f
    sift = cv2.SIFT_create()
    frame_kp, frame_desc = sift.detectAndCompute(frame_gray, None)
    if frame_desc is None or len(frame_desc) < 2:
        return None

    counts: list[tuple[int, BrandLogo, list]] = []
    for logo in gallery:
        if logo.descriptors is None:
            counts.append((0, logo, []))
            continue
        matches = _ratio_matches(logo.descriptors, frame_desc)
        counts.append((len(matches), logo, matches))
    counts.sort(key=lambda c: c[0], reverse=True)

    best_count, best_logo, best_matches = counts[0]
    runner = counts[1] if len(counts) > 1 else None
    if best_count < MIN_MATCHES:
        return None
    if runner and runner[0] > 0 and best_count < MIN_MARGIN * runner[0]:
        return None  # ambiguous between two brands

    pose, inliers = _pose_from_matches(best_logo, frame_kp, best_matches, scale_back)
    # Geometric gate: ratio-test matches alone false-positive on unrelated
    # panel text (letterforms look alike); a real logo's matches agree on one
    # similarity transform, scattered text matches don't.
    if pose is None or inliers < MIN_POSE_INLIERS or inliers < MIN_INLIER_RATIO * best_count:
        return None
    return BrandMatch(
        brand=best_logo.brand,
        match_count=best_count,
        runner_up=runner[1].brand if runner else None,
        runner_up_count=runner[0] if runner else 0,
        pose=pose,
        inliers=inliers,
    )


def main() -> int:
    if cv2 is None:
        print("OpenCV unavailable")
        return 1
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    frame_path = Path(args[0])
    brands_dir = Path(args[args.index("--brands-dir") + 1]) if "--brands-dir" in args else (
        Path(__file__).resolve().parents[3] / "data" / "brands"
    )
    frame = cv2.imread(str(frame_path))
    if frame is None:
        print(f"cannot read frame: {frame_path}")
        return 1
    gallery = load_gallery(brands_dir)
    print(f"gallery: {[g.brand for g in gallery]}")
    result = detect_brand(frame, gallery)
    if result is None:
        print("brand: NONE (no match or ambiguous)")
        return 2
    print(f"brand: {result.brand}  matches={result.match_count}  "
          f"runner_up={result.runner_up}({result.runner_up_count})  inliers={result.inliers}")
    if result.pose:
        p = result.pose
        print(f"pose: center=({p.center_x:.0f},{p.center_y:.0f}) "
              f"scale={p.scale:.3f} rot={np.degrees(p.rotation):.1f}deg score={p.score:.2f}")
    return 0


if __name__ == "__main__":
    main()
