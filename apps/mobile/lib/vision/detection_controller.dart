import 'dart:async';

import 'package:flutter/foundation.dart';

import 'frame_source.dart';
import 'geometry.dart';
import 'vision_match_client.dart';

enum DetectionPhase { idle, scanning, matched, rejected }

@immutable
class DetectionState {
  const DetectionState({
    required this.phase,
    this.matchScore,
    this.templateId,
    this.failureReason,
    this.polygons = const <ProjectedButton>[],
  });

  final DetectionPhase phase;
  final double? matchScore;
  final String? templateId;
  final String? failureReason;
  final List<ProjectedButton> polygons;

  static const DetectionState idle = DetectionState(phase: DetectionPhase.idle);
}

/// Drives a ~1 fps detect loop: grab frame -> match -> emit state.
/// Pure logic (no widgets); inject [source] and [matcher] for tests. Tests
/// drive [tick] directly; [start] wires it to a periodic timer.
///
/// Single-use: after [stop] the instance is terminal; create a new controller
/// for a new session. The owning widget should dispose [state].
class DetectionController {
  DetectionController({
    required FrameSource source,
    required Future<VisionMatchResult> Function(Uint8List frame) matcher,
    Duration interval = const Duration(seconds: 1),
    int lockThreshold = 2,
  })  : _source = source,
        _matcher = matcher,
        _interval = interval,
        _lockThreshold = lockThreshold;

  final FrameSource _source;
  final Future<VisionMatchResult> Function(Uint8List) _matcher;
  final Duration _interval;
  final int _lockThreshold;

  final ValueNotifier<DetectionState> state =
      ValueNotifier<DetectionState>(DetectionState.idle);

  Timer? _timer;
  bool _inFlight = false;
  bool _stopped = false;
  int _consecutiveAccepts = 0;

  Future<void> start() async {
    await _source.start();
    state.value = const DetectionState(phase: DetectionPhase.scanning);
    _timer = Timer.periodic(_interval, (_) => tick());
  }

  /// One detect cycle. Public so tests can drive it deterministically.
  Future<void> tick() async {
    if (_inFlight) return;
    _inFlight = true;
    try {
      final frame = await _source.grabFrame();
      final result = await _matcher(frame);
      if (result.accepted) {
        _consecutiveAccepts += 1;
        final locked = _consecutiveAccepts >= _lockThreshold;
        state.value = DetectionState(
          phase: locked ? DetectionPhase.matched : DetectionPhase.scanning,
          matchScore: result.matchScore,
          templateId: result.templateId,
          polygons: result.projectedButtons,
        );
      } else {
        _consecutiveAccepts = 0;
        state.value = DetectionState(
          phase: DetectionPhase.rejected,
          failureReason: result.failureReason,
        );
      }
    } catch (_) {
      _consecutiveAccepts = 0;
      state.value = const DetectionState(
        phase: DetectionPhase.rejected,
        failureReason: 'network',
      );
    } finally {
      _inFlight = false;
    }
  }

  Future<void> stop() async {
    if (_stopped) return;
    _stopped = true;
    _timer?.cancel();
    _timer = null;
    await _source.stop();
  }
}
