import 'match_confidence_state.dart';

class TrackingConfidenceMonitor {
  bool shouldStopHighlight(MatchConfidenceState confidence) =>
      !confidence.canShowHighlight;
}
