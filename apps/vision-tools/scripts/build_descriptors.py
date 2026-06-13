from __future__ import annotations

import argparse

import numpy as np


def build_descriptors(image_path: str, out_path: str) -> int:
    """Extract ORB keypoints+descriptors from an image, save to a .npz. Returns count."""
    import cv2

    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"cannot read image: {image_path}")
    orb = cv2.ORB_create(nfeatures=1500)
    keypoints, descriptors = orb.detectAndCompute(img, None)
    if descriptors is None:
        raise ValueError(f"no ORB features in {image_path}")
    points = np.array([kp.pt for kp in keypoints], dtype=np.float32)
    np.savez(out_path, keypoints=points, descriptors=descriptors.astype(np.uint8))
    return len(points)


def load_descriptors(npz_path: str) -> tuple[np.ndarray, np.ndarray]:
    data = np.load(npz_path)
    return data["keypoints"], data["descriptors"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ORB descriptor .npz from a template image")
    parser.add_argument("image")
    parser.add_argument("output")
    args = parser.parse_args()
    count = build_descriptors(args.image, args.output)
    print(f"wrote {count} descriptors to {args.output}")


if __name__ == "__main__":
    main()
