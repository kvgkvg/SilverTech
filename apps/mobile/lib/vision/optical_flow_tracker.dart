import 'match_confidence_state.dart';

/// Tracks camera motion using optical flow vectors to invalidate AR highlight confidence.
class OpticalFlowTracker {
  /// Evaluates stability and invalidates matching confidence if the camera is unstable/moving.
  ///
  /// Takes the [previous] confidence state and a boolean [stable] indicating whether
  /// the device was steady. Returns the previous state if stable, or resets to a
  /// rejected zero-confidence state if motion is detected.
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
