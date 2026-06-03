import 'package:silvertech_mobile/guidance/instruction_player.dart';

void main() {
  final player = InstructionPlayer(<GuidanceStep>[
    const GuidanceStep(
      stepNumber: 1,
      instructionVi: 'Nhan nut Giat nhanh.',
      buttonId: 'quick_wash',
      expectedResult: 'Da chon giat nhanh.',
    ),
    const GuidanceStep(
      stepNumber: 2,
      instructionVi: 'Nhan nut Bat dau.',
      buttonId: 'start_pause',
      expectedResult: 'May bat dau chay.',
    ),
  ]);

  assert(player.current?.buttonId == 'quick_wash');
  assert(player.canGoNext);
  assert(!player.canGoPrevious);
  player.next();
  assert(player.current?.buttonId == 'start_pause');
  assert(player.canGoPrevious);
}
