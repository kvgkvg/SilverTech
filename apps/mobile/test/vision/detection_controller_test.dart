import 'dart:async';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:silvertech_mobile/vision/detection_controller.dart';
import 'package:silvertech_mobile/vision/frame_source.dart';
import 'package:silvertech_mobile/vision/vision_match_client.dart';

class _FakeSource implements FrameSource {
  int started = 0;
  int stopped = 0;
  @override
  Future<void> start() async => started++;
  @override
  Future<Uint8List> grabFrame() async => Uint8List.fromList(<int>[1]);
  @override
  Future<void> stop() async => stopped++;
}

void main() {
  test('locks to matched after lockThreshold consecutive accepts', () async {
    final controller = DetectionController(
      source: _FakeSource(),
      matcher: (_) async => const VisionMatchResult(
          accepted: true, templateId: 't1', matchScore: 0.4),
      lockThreshold: 2,
    );

    await controller.tick();
    expect(controller.state.value.phase, DetectionPhase.scanning);
    await controller.tick();
    expect(controller.state.value.phase, DetectionPhase.matched);
    expect(controller.state.value.templateId, 't1');
    expect(controller.state.value.matchScore, 0.4);
  });

  test('rejected resets the accept streak', () async {
    var accept = true;
    final controller = DetectionController(
      source: _FakeSource(),
      matcher: (_) async => accept
          ? const VisionMatchResult(accepted: true, templateId: 't1')
          : const VisionMatchResult(
              accepted: false, failureReason: 'low_confidence'),
      lockThreshold: 2,
    );

    await controller.tick(); // accept #1 -> scanning
    accept = false;
    await controller.tick(); // reject -> rejected, streak reset
    expect(controller.state.value.phase, DetectionPhase.rejected);
    expect(controller.state.value.failureReason, 'low_confidence');
    accept = true;
    await controller.tick(); // accept #1 again -> scanning (not matched)
    expect(controller.state.value.phase, DetectionPhase.scanning);
  });

  test('drops overlapping ticks while a match is in flight', () async {
    final gate = Completer<void>();
    var calls = 0;
    final controller = DetectionController(
      source: _FakeSource(),
      matcher: (_) async {
        calls++;
        await gate.future;
        return const VisionMatchResult(accepted: true);
      },
      lockThreshold: 1,
    );

    final first = controller.tick(); // enters, awaits gate
    await controller.tick(); // dropped (in flight)
    expect(calls, 1);
    gate.complete();
    await first;
    expect(calls, 1);
  });

  test('matcher error surfaces as rejected and loop survives', () async {
    var fail = true;
    final controller = DetectionController(
      source: _FakeSource(),
      matcher: (_) async {
        if (fail) throw Exception('boom');
        return const VisionMatchResult(accepted: true);
      },
      lockThreshold: 1,
    );

    await controller.tick();
    expect(controller.state.value.phase, DetectionPhase.rejected);
    expect(controller.state.value.failureReason, 'network');
    fail = false;
    await controller.tick();
    expect(controller.state.value.phase, DetectionPhase.matched);
  });

  test('stop cancels and stops source exactly once (idempotent)', () async {
    final source = _FakeSource();
    final controller = DetectionController(
      source: source,
      matcher: (_) async => const VisionMatchResult(accepted: false),
    );
    await controller.start();
    expect(source.started, 1);
    await controller.stop();
    await controller.stop();
    expect(source.stopped, 1);
  });
}
