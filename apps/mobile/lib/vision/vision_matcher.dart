import 'match_confidence_state.dart';

class VisionMatchResult {
  const VisionMatchResult({required this.templateId, required this.confidence});
  final String templateId;
  final MatchConfidenceState confidence;
}

class VisionMatcher {
  VisionMatchResult evaluateSyntheticMatch({
    required String templateId,
    required int inlierCount,
    required int totalKeypoints,
    required double reprojectionError,
  }) {
    return VisionMatchResult(
      templateId: templateId,
      confidence: MatchConfidenceState.score(
        inlierCount: inlierCount,
        totalKeypoints: totalKeypoints,
        reprojectionError: reprojectionError,
      ),
    );
  }
}
