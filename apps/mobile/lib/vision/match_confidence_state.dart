class MatchConfidenceState {
  const MatchConfidenceState({
    required this.accepted,
    required this.matchScore,
    required this.inlierCount,
    required this.inlierRatio,
    required this.reprojectionError,
    this.failureReason,
  });

  final bool accepted;
  final double matchScore;
  final int inlierCount;
  final double inlierRatio;
  final double reprojectionError;
  final String? failureReason;

  bool get canShowHighlight => accepted && failureReason == null;

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
