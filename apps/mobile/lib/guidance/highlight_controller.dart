import '../vision/geometry.dart';
import '../vision/match_confidence_state.dart';
import '../vision/overlay_renderer.dart';
import 'instruction_player.dart';

class HighlightController {
  HighlightController({OverlayRenderer renderer = const OverlayRenderer()})
    : _renderer = renderer;
  final OverlayRenderer _renderer;

  List<ProjectedButton> highlightsForStep({
    required MatchConfidenceState confidence,
    required List<ProjectedButton> projectedButtons,
    required GuidanceStep? step,
  }) {
    return _renderer.visibleHighlights(
      confidence: confidence,
      projectedButtons: projectedButtons,
      activeButtonId: step?.buttonId,
    );
  }
}
