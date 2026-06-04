import 'package:flutter_test/flutter_test.dart';
import 'package:silvertech_mobile/guidance/instruction_player.dart';

void main() {
  test('advances through guidance steps', () {
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

    expect(player.current?.buttonId, 'quick_wash');
    expect(player.canGoNext, isTrue);
    expect(player.canGoPrevious, isFalse);

    player.next();

    expect(player.current?.buttonId, 'start_pause');
    expect(player.canGoPrevious, isTrue);
  });
}
