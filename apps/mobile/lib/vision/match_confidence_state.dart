/// Immutable representation of the vision alignment confidence and safety gates.
class MatchConfidenceState {
  /// Creates a new match confidence state instance.
  const MatchConfidenceState({
    required this.accepted,
    required this.matchScore,
    required this.inlierCount,
    required this.inlierRatio,
    required this.reprojectionError,
    this.failureReason,
  });

  /// Whether the alignment passed all geometric confidence thresholds.
  final bool accepted;

  /// Combined score in [0.0, 1.0] representing visual correlation quality.
  final double matchScore;

  /// Number of RANSAC inlier keypoints matching the template.
  final int inlierCount;

  /// Ratio of inlier matches / total keypoints in template.
  final double inlierRatio;

  /// Average reprojection error of matched inliers in pixels.
  final double reprojectionError;

  /// Reason for match failure (e.g. 'low_confidence', 'no_logo'), or null if accepted.
  final String? failureReason;

  /// Safety gate determining if the client is allowed to draw the AR overlay.
  bool get canShowHighlight => accepted && failureReason == null;

  /// Computes the match confidence scores based on keypoint matching metrics.
  ///
  /// Evaluates geometric safety gates: minimum 4 inliers, minimum 50% inlier ratio,
  /// and maximum 5.0 pixel reprojection error. Returns the resulting state.
  static MatchConfidenceState score({
    required int inlierCount,
    required int totalKeypoints,
    required double reprojectionError,
  }) {
    final ratio = totalKeypoints <= 0 ? 0.0 : inlierCount / totalKeypoints;
    final score = (ratio * (1.0 - (reprojectionError / 50.0).clamp(0.0, 1.0)))
        .clamp(0.0, 1.0);
    String? reason;
    if (inlierCount < 4 || ratio < 0.5 || reprojectionError > 5.0) {
      reason = 'low_confidence';
    }
    return MatchConfidenceState(
      accepted: reason == null,
      matchScore: score,
      inlierCount: inlierCount,
      inlierRatio: ratio,
      reprojectionError: reprojectionError,
      failureReason: reason,
    );
  }
}
