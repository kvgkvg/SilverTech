# Live Detection Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the mobile camera to the real backend ORB matcher so the app does live ~1 fps detection instead of returning a hardcoded template with a fake score.

**Architecture:** A `FrameSource` grabs JPEG frames (camera plugin `takePicture` on web/mobile; bundled-image fallback on Linux/no-camera). A pure-logic `DetectionController` runs a ~1 fps loop: grab → `POST /api/vision/match` → emit a `DetectionState` (scanning/matched/rejected) with backend-returned projected polygons. `main.dart` drives the camera screen from that state and overlays the polygons. The `button_id` validation gate in guidance stays unchanged downstream.

**Tech Stack:** Flutter 3.44.1 / Dart 3, `http ^1.2.0` (multipart), `camera ^0.11.0` (incl. `camera_web`), existing `geometry.dart` polygon types, `flutter_test` + `package:http/testing.dart` MockClient.

**Refinement vs spec:** the design doc described raw `getUserMedia → canvas → toBlob`. This plan instead uses the `camera` plugin's `takePicture()`, which works on web via `camera_web`. Same outcome (JPEG frame from the webcam), one cross-platform code path, no `dart:js_interop`.

**Backend response shape** (`POST /api/vision/match`, multipart: `file` part + `brand`/`appliance_type` fields):
```json
{ "accepted": true, "template_id": "...", "match_score": 0.39,
  "inlier_count": 798, "inlier_ratio": 0.13, "reprojection_error": 1.04,
  "failure_reason": null, "recovery_action": null,
  "projected_buttons": [ {"button_id": "start",
    "polygon": [{"x":10.0,"y":20.0},{"x":90.0,"y":20.0},{"x":90.0,"y":70.0},{"x":10.0,"y":70.0}]} ] }
```

**Test commands run from `apps/mobile/`.** All Dart code lives under `apps/mobile/lib/`, tests under `apps/mobile/test/`.

---

### Task 1: VisionMatchClient + VisionMatchResult

**Files:**
- Create: `apps/mobile/lib/vision/vision_match_client.dart`
- Test: `apps/mobile/test/vision/vision_match_client_test.dart`

- [ ] **Step 1: Write the failing test**

```dart
// apps/mobile/test/vision/vision_match_client_test.dart
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:silvertech_mobile/templates/template_repository_client.dart';
import 'package:silvertech_mobile/vision/vision_match_client.dart';

void main() {
  test('posts multipart frame and parses accepted result', () async {
    late http.Request captured;
    final client = VisionMatchClient(
      baseUrl: 'http://api.test',
      httpClient: MockClient((http.Request request) async {
        captured = request;
        return http.Response(
          jsonEncode(<String, Object?>{
            'accepted': true,
            'template_id': 'template_panasonic_microwave_nn_gt35hm_v1',
            'match_score': 0.39,
            'failure_reason': null,
            'projected_buttons': <Object?>[
              <String, Object?>{
                'button_id': 'start',
                'polygon': <Object?>[
                  <String, Object?>{'x': 10.0, 'y': 20.0},
                  <String, Object?>{'x': 90.0, 'y': 20.0},
                  <String, Object?>{'x': 90.0, 'y': 70.0},
                  <String, Object?>{'x': 10.0, 'y': 70.0},
                ],
              },
            ],
          }),
          200,
        );
      }),
    );

    final result = await client.match(
      Uint8List.fromList('FAKEJPEG'.codeUnits),
      brand: 'Panasonic',
      applianceType: 'microwave',
    );

    expect(captured.method, 'POST');
    expect(captured.url.path, '/api/vision/match');
    expect(captured.headers['content-type'], contains('multipart/form-data'));
    expect(captured.body, contains('Panasonic'));
    expect(captured.body, contains('FAKEJPEG'));
    expect(result.accepted, isTrue);
    expect(result.templateId, 'template_panasonic_microwave_nn_gt35hm_v1');
    expect(result.matchScore, 0.39);
    expect(result.projectedButtons.single.buttonId, 'start');
    expect(result.projectedButtons.single.polygon.length, 4);
    expect(result.projectedButtons.single.polygon.first.x, 10.0);
  });

  test('throws FriendlyBackendException on 5xx', () async {
    final client = VisionMatchClient(
      baseUrl: 'http://api.test',
      httpClient: MockClient((http.Request request) async {
        return http.Response(
          jsonEncode(<String, Object?>{
            'detail': <String, Object?>{
              'message_vi': 'Loi may chu.',
              'recovery_action': 'rescan',
            },
          }),
          502,
        );
      }),
    );

    expect(
      () => client.match(Uint8List.fromList('X'.codeUnits)),
      throwsA(isA<FriendlyBackendException>()
          .having((e) => e.statusCode, 'statusCode', 502)),
    );
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/mobile && flutter test test/vision/vision_match_client_test.dart`
Expected: FAIL — `vision_match_client.dart` / `VisionMatchClient` not found.

- [ ] **Step 3: Write minimal implementation**

```dart
// apps/mobile/lib/vision/vision_match_client.dart
import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../templates/template_repository_client.dart'
    show FriendlyBackendException;
import 'geometry.dart';

class VisionMatchResult {
  const VisionMatchResult({
    required this.accepted,
    this.templateId,
    this.matchScore,
    this.failureReason,
    this.projectedButtons = const <ProjectedButton>[],
  });

  final bool accepted;
  final String? templateId;
  final double? matchScore;
  final String? failureReason;
  final List<ProjectedButton> projectedButtons;

  factory VisionMatchResult.fromJson(Map<String, Object?> json) {
    final rawButtons =
        (json['projected_buttons'] as List<Object?>?) ?? const <Object?>[];
    return VisionMatchResult(
      accepted: json['accepted'] as bool? ?? false,
      templateId: json['template_id'] as String?,
      matchScore: (json['match_score'] as num?)?.toDouble(),
      failureReason: json['failure_reason'] as String?,
      projectedButtons: rawButtons
          .whereType<Map<String, Object?>>()
          .map(_buttonFromJson)
          .toList(),
    );
  }

  static ProjectedButton _buttonFromJson(Map<String, Object?> json) {
    final rawPolygon = (json['polygon'] as List<Object?>?) ?? const <Object?>[];
    return ProjectedButton(
      buttonId: json['button_id'] as String? ?? '',
      polygon: rawPolygon
          .whereType<Map<String, Object?>>()
          .map((p) =>
              Point2((p['x'] as num).toDouble(), (p['y'] as num).toDouble()))
          .toList(),
    );
  }
}

class VisionMatchClient {
  VisionMatchClient({required this.baseUrl, http.Client? httpClient})
      : _httpClient = httpClient ?? http.Client();

  final String baseUrl;
  final http.Client _httpClient;

  Uri get uri => Uri.parse('$baseUrl/api/vision/match');

  Future<VisionMatchResult> match(
    Uint8List jpegBytes, {
    String? brand,
    String? applianceType,
  }) async {
    final request = http.MultipartRequest('POST', uri);
    if (brand != null) request.fields['brand'] = brand;
    if (applianceType != null) request.fields['appliance_type'] = applianceType;
    request.files.add(
      http.MultipartFile.fromBytes('file', jpegBytes, filename: 'frame.jpg'),
    );

    final streamed = await _httpClient.send(request);
    final response = await http.Response.fromStream(streamed);

    if (response.statusCode < 200 || response.statusCode >= 300) {
      final decoded = jsonDecode(response.body);
      final detail = decoded is Map<String, Object?> &&
              decoded['detail'] is Map<String, Object?>
          ? decoded['detail'] as Map<String, Object?>
          : (decoded is Map<String, Object?>
              ? decoded
              : const <String, Object?>{});
      throw FriendlyBackendException(
        messageVi: detail['message_vi'] as String? ?? 'Khong nhan dien duoc.',
        recoveryAction: detail['recovery_action'] as String? ?? 'rescan',
        statusCode: response.statusCode,
      );
    }

    return VisionMatchResult.fromJson(
      jsonDecode(response.body) as Map<String, Object?>,
    );
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/mobile && flutter test test/vision/vision_match_client_test.dart`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add apps/mobile/lib/vision/vision_match_client.dart apps/mobile/test/vision/vision_match_client_test.dart
git commit -m "feat(mobile): VisionMatchClient posts frames to /api/vision/match"
```

---

### Task 2: FrameSource interface + FileFrameSource fallback

**Files:**
- Create: `apps/mobile/lib/vision/frame_source.dart`
- Create: `apps/mobile/lib/vision/frame_source_file.dart`
- Test: `apps/mobile/test/vision/frame_source_file_test.dart`

- [ ] **Step 1: Write the failing test**

```dart
// apps/mobile/test/vision/frame_source_file_test.dart
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:silvertech_mobile/vision/frame_source_file.dart';

void main() {
  test('returns the injected bytes on each grab', () async {
    final bytes = Uint8List.fromList(<int>[1, 2, 3, 4]);
    var loads = 0;
    final source = FileFrameSource(loader: () async {
      loads++;
      return bytes;
    });

    await source.start();
    expect(await source.grabFrame(), bytes);
    expect(await source.grabFrame(), bytes);
    expect(loads, 1); // cached after start
    await source.stop();
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/mobile && flutter test test/vision/frame_source_file_test.dart`
Expected: FAIL — `frame_source_file.dart` / `FileFrameSource` not found.

- [ ] **Step 3: Write minimal implementation**

```dart
// apps/mobile/lib/vision/frame_source.dart
import 'dart:typed_data';

/// Source of camera frames for the detection loop. Implementations grab the
/// current frame as JPEG bytes.
abstract class FrameSource {
  Future<void> start();
  Future<Uint8List> grabFrame();
  Future<void> stop();
}
```

```dart
// apps/mobile/lib/vision/frame_source_file.dart
import 'dart:typed_data';

import 'package:flutter/services.dart' show rootBundle;

import 'frame_source.dart';

/// Frame source that returns a fixed image's bytes on every grab. Used as the
/// no-camera fallback (Linux desktop / dev) and is fully testable by injecting
/// [loader].
class FileFrameSource implements FrameSource {
  FileFrameSource({required Future<Uint8List> Function() loader})
      : _loader = loader;

  /// Loads a bundled asset (default: the demo Panasonic panel).
  factory FileFrameSource.asset(
      [String assetPath = 'assets/test/panel.jpg']) {
    return FileFrameSource(
      loader: () async =>
          (await rootBundle.load(assetPath)).buffer.asUint8List(),
    );
  }

  final Future<Uint8List> Function() _loader;
  Uint8List? _cached;

  @override
  Future<void> start() async {
    _cached = await _loader();
  }

  @override
  Future<Uint8List> grabFrame() async {
    return _cached ??= await _loader();
  }

  @override
  Future<void> stop() async {
    _cached = null;
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/mobile && flutter test test/vision/frame_source_file_test.dart`
Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add apps/mobile/lib/vision/frame_source.dart apps/mobile/lib/vision/frame_source_file.dart apps/mobile/test/vision/frame_source_file_test.dart
git commit -m "feat(mobile): FrameSource interface + FileFrameSource fallback"
```

---

### Task 3: CameraFrameSource + factory + bundled panel asset

No unit test (needs real camera hardware); verified on Chrome in Task 7. The plan keeps this thin so the untested surface is minimal.

**Files:**
- Create: `apps/mobile/lib/vision/frame_source_camera.dart`
- Create: `apps/mobile/lib/vision/frame_source_factory.dart`
- Create: `apps/mobile/assets/test/panel.jpg` (downscaled demo panel)
- Modify: `apps/mobile/pubspec.yaml` (declare the asset)

- [ ] **Step 1: Generate the downscaled fallback asset**

Run (from repo root, `silvertech` conda env active for cv2):
```bash
mkdir -p apps/mobile/assets/test
python3 -c "import cv2; im=cv2.imread('data/templates/panasonic_microwave_nn_gt35hm.png'); h,w=im.shape[:2]; s=720.0/max(h,w); cv2.imwrite('apps/mobile/assets/test/panel.jpg', cv2.resize(im,(int(w*s),int(h*s))))"
ls -la apps/mobile/assets/test/panel.jpg
```
Expected: a small (<300 KB) `panel.jpg` exists.

- [ ] **Step 2: Declare the asset in pubspec**

In `apps/mobile/pubspec.yaml`, under `flutter:` → `assets:`, add the line:
```yaml
    - assets/test/panel.jpg
```

- [ ] **Step 3: Write CameraFrameSource**

```dart
// apps/mobile/lib/vision/frame_source_camera.dart
import 'dart:typed_data';

import 'package:camera/camera.dart';

import 'frame_source.dart';

/// Frame source backed by the `camera` plugin. Works on web (camera_web) and
/// mobile via takePicture(); the `camera` plugin has no Linux implementation,
/// so [createFrameSource] falls back to [FileFrameSource] there.
class CameraFrameSource implements FrameSource {
  CameraFrameSource(this.controller);

  final CameraController controller;

  static Future<CameraFrameSource> open() async {
    final cameras = await availableCameras();
    if (cameras.isEmpty) {
      throw CameraException('no_camera', 'No camera found on this device.');
    }
    final camera = cameras.firstWhere(
      (c) => c.lensDirection == CameraLensDirection.back,
      orElse: () => cameras.first,
    );
    final controller =
        CameraController(camera, ResolutionPreset.medium, enableAudio: false);
    await controller.initialize();
    return CameraFrameSource(controller);
  }

  @override
  Future<void> start() async {
    if (!controller.value.isInitialized) {
      await controller.initialize();
    }
  }

  @override
  Future<Uint8List> grabFrame() async {
    final file = await controller.takePicture();
    return file.readAsBytes();
  }

  @override
  Future<void> stop() async {
    await controller.dispose();
  }
}
```

- [ ] **Step 4: Write the factory**

```dart
// apps/mobile/lib/vision/frame_source_factory.dart
import 'frame_source.dart';
import 'frame_source_camera.dart';
import 'frame_source_file.dart';

/// Returns a camera-backed frame source when a camera is available, otherwise
/// the bundled-image fallback (Linux desktop / no webcam).
Future<FrameSource> createFrameSource() async {
  try {
    return await CameraFrameSource.open();
  } catch (_) {
    return FileFrameSource.asset();
  }
}
```

- [ ] **Step 5: Verify it compiles**

Run: `cd apps/mobile && flutter analyze lib/vision/frame_source_camera.dart lib/vision/frame_source_factory.dart`
Expected: "No issues found!" (warnings about unused are acceptable; errors are not).

- [ ] **Step 6: Commit**

```bash
git add apps/mobile/lib/vision/frame_source_camera.dart apps/mobile/lib/vision/frame_source_factory.dart apps/mobile/assets/test/panel.jpg apps/mobile/pubspec.yaml
git commit -m "feat(mobile): CameraFrameSource (takePicture) + file fallback factory"
```

---

### Task 4: DetectionController (the ~1 fps loop)

**Files:**
- Create: `apps/mobile/lib/vision/detection_controller.dart`
- Test: `apps/mobile/test/vision/detection_controller_test.dart`

- [ ] **Step 1: Write the failing test**

```dart
// apps/mobile/test/vision/detection_controller_test.dart
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/mobile && flutter test test/vision/detection_controller_test.dart`
Expected: FAIL — `detection_controller.dart` not found.

- [ ] **Step 3: Write minimal implementation**

```dart
// apps/mobile/lib/vision/detection_controller.dart
import 'dart:async';
import 'dart:typed_data';

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/mobile && flutter test test/vision/detection_controller_test.dart`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add apps/mobile/lib/vision/detection_controller.dart apps/mobile/test/vision/detection_controller_test.dart
git commit -m "feat(mobile): DetectionController ~1fps loop with lock-on + in-flight drop"
```

---

### Task 5: Backend gateway — add match() + fetchTemplate()

`HttpSilverBackendGateway` already holds a `TemplateRepositoryClient`. Add a `VisionMatchClient` and expose `match()` + `fetchTemplate()` so the camera screen can run detection and then load the full template by id.

**Files:**
- Modify: `apps/mobile/lib/backend/silver_backend.dart`
- Test: `apps/mobile/test/backend_clients_test.dart` (add cases)

- [ ] **Step 1: Write the failing test (append inside the existing `main()` in `backend_clients_test.dart`)**

```dart
  test('backend.match delegates to VisionMatchClient with brand fields',
      () async {
    late http.Request captured;
    final matchClient = VisionMatchClient(
      baseUrl: 'http://api.test',
      httpClient: MockClient((http.Request request) async {
        captured = request;
        return http.Response(
          jsonEncode(<String, Object?>{
            'accepted': true,
            'template_id': 'template_panasonic_microwave_nn_gt35hm_v1',
            'match_score': 0.4,
            'projected_buttons': <Object?>[],
          }),
          200,
        );
      }),
    );
    final backend = HttpSilverBackendGateway(visionMatch: matchClient);

    final result = await backend.match(
      Uint8List.fromList('FAKEJPEG'.codeUnits),
      brand: 'Panasonic',
      applianceType: 'microwave',
    );

    expect(captured.url.path, '/api/vision/match');
    expect(result.accepted, isTrue);
    expect(result.templateId, 'template_panasonic_microwave_nn_gt35hm_v1');
  });
```

Add the imports at the top of `backend_clients_test.dart` (if not already present):
```dart
import 'dart:typed_data';
import 'package:silvertech_mobile/vision/vision_match_client.dart';
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/mobile && flutter test test/backend_clients_test.dart`
Expected: FAIL — `HttpSilverBackendGateway` has no `visionMatch` param / no `match` method.

- [ ] **Step 3: Modify `silver_backend.dart`**

Add the import near the other client imports:
```dart
import 'dart:typed_data';

import '../vision/vision_match_client.dart';
```

Extend the abstract gateway (`abstract class SilverBackendGateway`) with:
```dart
  Future<VisionMatchResult> match(
    Uint8List frame, {
    String? brand,
    String? applianceType,
  });

  Future<TemplateDetailDto> fetchTemplate(String templateId);
```

In `HttpSilverBackendGateway`, add the field + constructor wiring (extend the existing constructor's initializer list):
```dart
  HttpSilverBackendGateway({
    TemplateRepositoryClient? templates,
    GuidanceClient? guidance,
    VisionLogClient? visionLogs,
    VisionMatchClient? visionMatch,
  })  : _templates = templates ??
            TemplateRepositoryClient(baseUrl: defaultSilverTechApiBaseUrl),
        _guidance =
            guidance ?? GuidanceClient(baseUrl: defaultSilverTechApiBaseUrl),
        _visionLogs =
            visionLogs ?? VisionLogClient(baseUrl: defaultSilverTechApiBaseUrl),
        _visionMatch = visionMatch ??
            VisionMatchClient(baseUrl: defaultSilverTechApiBaseUrl);
```
Add the field with the others:
```dart
  final VisionMatchClient _visionMatch;
```
Add the methods (after `createGuidance`):
```dart
  @override
  Future<VisionMatchResult> match(
    Uint8List frame, {
    String? brand,
    String? applianceType,
  }) {
    return _visionMatch.match(frame, brand: brand, applianceType: applianceType);
  }

  @override
  Future<TemplateDetailDto> fetchTemplate(String templateId) {
    return _templates.fetchTemplate(templateId);
  }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/mobile && flutter test test/backend_clients_test.dart`
Expected: PASS (existing tests + the new one).

- [ ] **Step 5: Commit**

```bash
git add apps/mobile/lib/backend/silver_backend.dart apps/mobile/test/backend_clients_test.dart
git commit -m "feat(mobile): gateway.match() + fetchTemplate() for live detection"
```

---

### Task 6: Wire the camera screen to DetectionController

Replaces the hardcoded `_acceptBackendRecognition()` (`apps/mobile/lib/main.dart:306`) and the fake `_recognitionMatchScore = 0.94` (`main.dart:247`) with a live DetectionController loop. The implementer should Read `main.dart` around lines 240–500 and 1900–2030 first to place widgets per existing patterns. This task is verified by `flutter test` (existing widget test must stay green) plus the manual Chrome run in Task 7.

**Files:**
- Modify: `apps/mobile/lib/main.dart`

- [ ] **Step 1: Add fields to `_SilverPrototypeShellState`** (near the existing `_recognitionBusy` / `_recognitionMatchScore` / `_selectedTemplate` fields, ~line 245)

```dart
  DetectionController? _detection;
  List<ProjectedButton> _projectedButtons = const <ProjectedButton>[];
  String _scanStatusVi = 'Đang quét bảng điều khiển...';
```

Add imports at the top of `main.dart` (with the other local imports):
```dart
import 'vision/detection_controller.dart';
import 'vision/frame_source_factory.dart';
import 'vision/geometry.dart';
```

- [ ] **Step 2: Replace the body of `_acceptBackendRecognition()`** (`main.dart:306`-~331) with a loop-driven version

```dart
  Future<void> _startLiveDetection() async {
    setState(() {
      _toast = null;
      _recognitionBusy = true;
      _scanStatusVi = 'Đang quét bảng điều khiển...';
    });
    try {
      final source = await createFrameSource();
      final controller = DetectionController(
        source: source,
        matcher: (frame) => widget.backend.match(
          frame,
          brand: 'Panasonic',
          applianceType: 'microwave',
        ),
      );
      _detection = controller;
      controller.state.addListener(() => _onDetectionState(controller));
      await controller.start();
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _recognitionBusy = false;
        _toast = 'Không mở được camera.';
      });
    }
  }

  void _onDetectionState(DetectionController controller) {
    if (!mounted) return;
    final s = controller.state.value;
    switch (s.phase) {
      case DetectionPhase.scanning:
        setState(() {
          _scanStatusVi = 'Đang quét... (độ khớp '
              '${((s.matchScore ?? 0) * 100).round()}%)';
          _projectedButtons = s.polygons;
        });
        break;
      case DetectionPhase.rejected:
        setState(() {
          _scanStatusVi = 'Chưa rõ. Đưa camera gần hơn, tránh chói.';
          _projectedButtons = const <ProjectedButton>[];
        });
        break;
      case DetectionPhase.matched:
        _onTemplateMatched(s);
        break;
      case DetectionPhase.idle:
        break;
    }
  }

  Future<void> _onTemplateMatched(DetectionState s) async {
    final templateId = s.templateId;
    if (templateId == null) return;
    await _detection?.stop();
    _detection = null;
    try {
      final template = await widget.backend.fetchTemplate(templateId);
      if (!mounted) return;
      setState(() {
        _selectedTemplate = template;
        _recognitionMatchScore = s.matchScore ?? 0;
        _projectedButtons = s.polygons;
        _recognitionBusy = false;
        _scanStatusVi = 'Đã nhận diện ${template.brand}.';
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _recognitionBusy = false;
        _toast = 'Không tải được mẫu thiết bị.';
      });
    }
  }
```

- [ ] **Step 3: Update the call site + lifecycle**

- Find where `_acceptBackendRecognition` was invoked (the recognition button, ~line 478) and call `_startLiveDetection` instead.
- After a successful match the UI shows "Đã nhận diện ${brand}" + the existing flow's **Tiếp tục** affordance to navigate to the `voice` step (reuse the existing navigation that previously ran inside `_acceptBackendRecognition`). Do **not** auto-navigate; require the user tap.
- Add `dispose()` cleanup in `_SilverPrototypeShellState` (or stop on navigate-away):
```dart
  @override
  void dispose() {
    _detection?.stop();
    super.dispose();
  }
```
(If `_SilverPrototypeShellState` already has a `dispose()`, add the `_detection?.stop();` line to it instead of creating a second one.)

- [ ] **Step 4: Overlay the projected polygons**

Pass `_projectedButtons` into the camera preview overlay. Locate the widget that currently renders the static template boxes (it consumes `_selectedTemplate?.buttons`, ~lines 484–497) and render `_projectedButtons` polygons over the `CameraPreviewPanel` instead for the live path. Each `ProjectedButton.polygon` is a `List<Point2>` in template/image pixel space — draw it scaled to the preview box (reuse the existing overlay/scaling widget if one exists; otherwise a simple `CustomPaint` that maps polygon points into the preview rect).

- [ ] **Step 5: Verify existing tests + analyzer stay green**

Run:
```bash
cd apps/mobile && flutter analyze lib/main.dart && flutter test test/widget_test.dart
```
Expected: analyzer clean (no errors); `widget_test.dart` PASS. If `widget_test.dart` constructs `HttpSilverBackendGateway` or drives recognition, update it to the new method names so it compiles.

- [ ] **Step 6: Commit**

```bash
git add apps/mobile/lib/main.dart apps/mobile/test/widget_test.dart
git commit -m "feat(mobile): live detection loop drives camera screen + polygon overlay"
```

---

### Task 7: Full verification + Chrome manual check

**Files:** none (verification only).

- [ ] **Step 1: Run the full mobile Dart test suite**

Run: `cd apps/mobile && flutter test`
Expected: ALL PASS (new vision tests + backend tests + existing widget/guidance/ui tests).

- [ ] **Step 2: Static analysis**

Run: `cd apps/mobile && flutter analyze`
Expected: "No issues found!" (or only pre-existing warnings — no new errors).

- [ ] **Step 3: Backend up for the live check**

Run (repo root, `silvertech` env): `make seed-api && make run-api`
Confirm `POST /api/vision/match` is live:
```bash
curl -s -F file=@data/templates/panasonic_microwave_nn_gt35hm.png \
  -F brand=Panasonic -F appliance_type=microwave \
  http://127.0.0.1:8000/api/vision/match | python3 -c "import sys,json;print(json.load(sys.stdin)['accepted'])"
```
Expected: `True`.

- [ ] **Step 4: Manual Chrome run (user, has webcam)**

Run: `cd apps/mobile && flutter run -d chrome --dart-define=SILVERTECH_API_BASE_URL=http://localhost:8000`
- Grant camera permission.
- Point the webcam at the Panasonic microwave panel (or the printed/template image on screen).
- Expect: "Đang quét..." then "Đã nhận diện Panasonic" with button polygons overlaid; **Tiếp tục** proceeds to the voice/guidance step.
- Point at something else → "Chưa rõ..." recovery hint, no false lock.

- [ ] **Step 5: Final commit (if any verification fixups were needed)**

```bash
git add -A
git commit -m "test(mobile): verify live detection end-to-end on Chrome"
```

---

## Self-review notes

- **Spec coverage:** VisionMatchClient (spec component 1) → Task 1; FrameSource + impls (2) → Tasks 2–3; DetectionController (3) → Task 4; gateway.match (4) → Task 5; main.dart wiring + overlay (5) → Task 6; testing strategy → Tasks 1–7. The `button_id` gate is untouched (no task modifies guidance — correct).
- **Refinement logged:** camera-plugin `takePicture` replaces raw getUserMedia/canvas (lower risk, cross-platform). File fallback preserved for Linux/dev as decided.
- **Type consistency:** `VisionMatchResult`, `DetectionState`/`DetectionPhase`, `ProjectedButton{buttonId, polygon: List<Point2>}`, `Point2{x,y}` used consistently across tasks; gateway method names `match`/`fetchTemplate` match their call sites in Task 6.
- **Untested surfaces (documented, by necessity):** `CameraFrameSource`, `frame_source_factory`, and the `main.dart` widget tree are camera/UI-bound — verified via `flutter analyze` + manual Chrome run, not unit tests (sandbox has no camera).
