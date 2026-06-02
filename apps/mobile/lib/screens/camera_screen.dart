import '../guidance/highlight_controller.dart';
import '../guidance/instruction_player.dart';
import '../vision/geometry.dart';
import '../vision/match_confidence_state.dart';

class CameraScreenController {
  CameraScreenController({HighlightController? highlightController})
      : _highlightController = highlightController ?? HighlightController();

  final HighlightController _highlightController;
  String get instructionVi => 'Huong camera vao bang dieu khien.';

  List<ProjectedButton> highlights({
    required MatchConfidenceState confidence,
    required List<ProjectedButton> projectedButtons,
    required GuidanceStep? step,
  }) {
    return _highlightController.highlightsForStep(
      confidence: confidence,
      projectedButtons: projectedButtons,
      step: step,
    );
  }
}
