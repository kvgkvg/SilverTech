import 'package:silvertech_mobile/ui/rescan_guidance_ui.dart';
import 'package:silvertech_mobile/vision/geometry.dart';
import 'package:silvertech_mobile/vision/match_confidence_state.dart';
import 'package:silvertech_mobile/vision/overlay_renderer.dart';

void main() {
  final low = MatchConfidenceState.score(
    inlierCount: 1,
    totalKeypoints: 8,
    reprojectionError: 1,
  );

  assert(!low.canShowHighlight);
  assert(
    const OverlayRenderer()
        .visibleHighlights(
          confidence: low,
          projectedButtons: const <ProjectedButton>[],
          activeButtonId: 'quick_wash',
        )
        .isEmpty,
  );
  assert(RescanGuidanceMessages.messages['rescan']!.isNotEmpty);
}
