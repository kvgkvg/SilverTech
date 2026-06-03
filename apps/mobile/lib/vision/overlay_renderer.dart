import 'geometry.dart';
import 'match_confidence_state.dart';

class OverlayRenderer {
  const OverlayRenderer();

  List<ProjectedButton> visibleHighlights({
    required MatchConfidenceState confidence,
    required List<ProjectedButton> projectedButtons,
    required String? activeButtonId,
  }) {
    if (!confidence.canShowHighlight || activeButtonId == null) {
      return <ProjectedButton>[];
    }
    return projectedButtons
        .where((button) => button.buttonId == activeButtonId)
        .toList();
  }
}
