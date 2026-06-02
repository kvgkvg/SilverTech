class GuidanceStep {
  const GuidanceStep({
    required this.stepNumber,
    required this.instructionVi,
    required this.buttonId,
    required this.expectedResult,
  });

  final int stepNumber;
  final String instructionVi;
  final String buttonId;
  final String expectedResult;
}

class InstructionPlayer {
  InstructionPlayer(this.steps);
  final List<GuidanceStep> steps;
  int _index = 0;

  GuidanceStep? get current => steps.isEmpty ? null : steps[_index];
  bool get canGoNext => _index < steps.length - 1;
  bool get canGoPrevious => _index > 0;

  void next() {
    if (canGoNext) _index += 1;
  }

  void previous() {
    if (canGoPrevious) _index -= 1;
  }
}
