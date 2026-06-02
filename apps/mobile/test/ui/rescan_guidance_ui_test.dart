import '../../lib/ui/rescan_guidance_ui.dart';
import '../../lib/vision/geometry.dart';
import '../../lib/vision/match_confidence_state.dart';
import '../../lib/vision/overlay_renderer.dart';

void main() {
  final low = MatchConfidenceState.score(
    inlierCount: 1,
    totalKeypoints: 8,
    reprojectionError: 1,
  );

  assert(!low.canShowHighlight);
  assert(
    OverlayRenderer()
        .visibleHighlights(
          confidence: low,
          projectedButtons: const <ProjectedButton>[],
          activeButtonId: 'quick_wash',
        )
        .isEmpty,
  );
  assert(RescanGuidanceMessages.messages['rescan']!.isNotEmpty);
}
