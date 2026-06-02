# CV Matching Pipeline

1. Detect or select brand/logo.
2. Retrieve official candidate templates.
3. Extract ORB features, with SIFT comparison when available.
4. Match descriptors and filter good matches.
5. Estimate homography or affine transform.
6. Compute inlier count, inlier ratio, reprojection error, and geometry checks.
7. Reject low-confidence matches.
8. Project button boxes only when confidence passes.

QR anchors are not part of the primary localization method.
