import 'match_confidence_state.dart';

class OpticalFlowTracker {
  MatchConfidenceState updateAfterMotion(
    MatchConfidenceState previous, {
    required bool stable,
  }) {
    if (stable) return previous;
    return const MatchConfidenceState(
      accepted: false,
      matchScore: 0,
      inlierCount: 0,
      inlierRatio: 0,
      reprojectionError: double.infinity,
      failureReason: 'low_confidence',
    );
  }
}
