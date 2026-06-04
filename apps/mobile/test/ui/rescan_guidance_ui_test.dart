import 'package:flutter_test/flutter_test.dart';
import 'package:silvertech_mobile/ui/rescan_guidance_ui.dart';
import 'package:silvertech_mobile/vision/geometry.dart';
import 'package:silvertech_mobile/vision/match_confidence_state.dart';
import 'package:silvertech_mobile/vision/overlay_renderer.dart';

void main() {
  test('low confidence hides highlights and exposes rescan copy', () {
    final low = MatchConfidenceState.score(
      inlierCount: 1,
      totalKeypoints: 8,
      reprojectionError: 1,
    );

    expect(low.canShowHighlight, isFalse);
    expect(
      const OverlayRenderer().visibleHighlights(
        confidence: low,
        projectedButtons: const <ProjectedButton>[],
        activeButtonId: 'quick_wash',
      ),
      isEmpty,
    );
    expect(RescanGuidanceMessages.messages['rescan'], isNotEmpty);
  });
}
