// dart run apps/mobile/debug/vision_pipeline_debugger.dart [options]
//
// Options:
//   --brand=<name>         brand label (default: panasonic)
//   --inliers=<n>          inlier keypoint count (default: 8)
//   --keypoints=<n>        total keypoint count (default: 12)
//   --reproj=<f>           reprojection error in px (default: 2.3)
//   --stable=<bool>        optical flow stable? (default: true)
//   --active=<button_id>   active button to highlight (default: btn_power)
//   --sweep                sweep inliers×reproj grid, show accept/reject map
//   --help                 show this help

import 'dart:io';
import 'dart:math' as math;
import '../lib/vision/brand_matcher.dart';
import '../lib/vision/vision_matcher.dart';
import '../lib/vision/match_confidence_state.dart';
import '../lib/vision/homography_projector.dart';
import '../lib/vision/optical_flow_tracker.dart';
import '../lib/vision/tracking_confidence_monitor.dart';
import '../lib/vision/tracking_reset_controller.dart';
import '../lib/vision/overlay_renderer.dart';
import '../lib/vision/geometry.dart';

// ── ANSI helpers ──────────────────────────────────────────────────────────────
const _reset = '\x1B[0m';
const _bold = '\x1B[1m';
const _dim = '\x1B[2m';
const _green = '\x1B[32m';
const _red = '\x1B[31m';
const _yellow = '\x1B[33m';
const _cyan = '\x1B[36m';
const _white = '\x1B[37m';
const _bgGreen = '\x1B[42m';
const _bgRed = '\x1B[41m';

String ok(String s) => '$_green$s$_reset';
String fail(String s) => '$_red$s$_reset';
String warn(String s) => '$_yellow$s$_reset';
String dim(String s) => '$_dim$s$_reset';
String bold(String s) => '$_bold$s$_reset';
String cyan(String s) => '$_cyan$s$_reset';

// ── Layout helpers ─────────────────────────────────────────────────────────────
const int _w = 62;

void _rule([String char = '─']) => print(dim('─' * _w));

void _header(String title) {
  print('');
  _rule();
  final pad = ((_w - title.length - 2) / 2).floor();
  final extra = (_w - title.length - 2) % 2;
  print('$_bold$_cyan'
      '│${' ' * pad} $title ${' ' * (pad + extra)}│'
      '$_reset');
  _rule();
}

void _stepBanner(int n, String name) {
  print('');
  print('$_bold  [$n] $name$_reset');
  print(dim('  ${'─' * (_w - 4)}'));
}

void _field(String label, String value, {String? note, bool? pass}) {
  final icon = pass == null ? '' : (pass ? ok('✓') : fail('✗'));
  final noteStr = note != null ? dim('  ← $note') : '';
  print('     ${dim(label.padRight(18))} ${pass == true ? ok(value) : pass == false ? fail(value) : value}$noteStr $icon');
}

void _verdict(bool accepted) {
  if (accepted) {
    print('\n     ${_bgGreen}${_white}${_bold}  ACCEPTED  $_reset');
  } else {
    print('\n     ${_bgRed}${_white}${_bold}  REJECTED  $_reset');
  }
}

// ── Thresholds (mirrors MatchConfidenceState.score) ───────────────────────────
const double _minInlierRatio = 0.5;
const double _maxReprojError = 5.0;
const int _minInlierCount = 4;

// ── Main ──────────────────────────────────────────────────────────────────────
void main(List<String> args) {
  final opts = _parseArgs(args);

  if (opts['help'] == 'true') {
    _printHelp();
    return;
  }

  if (opts['sweep'] == 'true') {
    _runSweep();
    return;
  }

  _runPipeline(opts);
}

// ── Single pipeline run ───────────────────────────────────────────────────────
void _runPipeline(Map<String, String> opts) {
  final brand = opts['brand']!;
  final inliers = int.parse(opts['inliers']!);
  final keypoints = int.parse(opts['keypoints']!);
  final reproj = double.parse(opts['reproj']!);
  final stable = opts['stable'] == 'true';
  final activeButton = opts['active']!;

  // Demo buttons on a synthetic 200×100 panel
  final demoButtons = <String, BBox>{
    'btn_power': const BBox(x: 10, y: 10, width: 40, height: 30),
    'btn_temp_up': const BBox(x: 60, y: 10, width: 40, height: 30),
    'btn_temp_down': const BBox(x: 110, y: 10, width: 40, height: 30),
    'btn_mode': const BBox(x: 160, y: 10, width: 30, height: 30),
  };

  // Identity-ish homography with slight perspective warp for demo
  final demoMatrix = <List<double>>[
    [1.02, 0.01, 5.0],
    [0.005, 1.015, 3.0],
    [0.0001, 0.00005, 1.0],
  ];

  _header('SilverTech Vision Pipeline Debugger');
  print(dim('  branch: 002-vision-debug   dart run debug/vision_pipeline_debugger.dart'));

  // ── Step 1: BrandMatcher ──────────────────────────────────────────────────
  _stepBanner(1, 'BrandMatcher');
  final bm = BrandMatcher();
  final brandMatch = bm.matchFromManualSelection(brand);
  _field('brand input', '"$brand"');
  if (brandMatch != null) {
    _field('match.brand', brandMatch.brand, pass: true);
    _field('match.confidence', brandMatch.confidence.toStringAsFixed(2), pass: true);
  } else {
    _field('result', 'null — no brand selected', pass: false);
  }

  // ── Step 2: MatchConfidenceState ──────────────────────────────────────────
  _stepBanner(2, 'MatchConfidenceState.score()');
  final ratio = keypoints <= 0 ? 0.0 : inliers / keypoints;
  final normalizedReproj = (reproj / 50.0).clamp(0.0, 1.0);
  final score = (ratio * (1.0 - normalizedReproj)).clamp(0.0, 1.0);

  _field('inliers', '$inliers',
      note: 'threshold ≥$_minInlierCount',
      pass: inliers >= _minInlierCount);
  _field('keypoints', '$keypoints');
  _field('inlierRatio', ratio.toStringAsFixed(3),
      note: 'threshold ≥$_minInlierRatio',
      pass: ratio >= _minInlierRatio);
  _field('reprojError', '${reproj}px',
      note: 'threshold ≤${_maxReprojError}px',
      pass: reproj <= _maxReprojError);
  _field('matchScore', score.toStringAsFixed(4));

  final conf = MatchConfidenceState.score(
    inlierCount: inliers,
    totalKeypoints: keypoints,
    reprojectionError: reproj,
  );
  _field('accepted', conf.accepted ? 'true' : 'false', pass: conf.accepted);
  if (conf.failureReason != null) {
    _field('failureReason', '"${conf.failureReason}"');
    final reasons = <String>[];
    if (inliers < _minInlierCount) reasons.add('inliers < $_minInlierCount');
    if (ratio < _minInlierRatio) reasons.add('ratio < $_minInlierRatio');
    if (reproj > _maxReprojError) reasons.add('reproj > ${_maxReprojError}px');
    print('     ${warn('↳ failed because: ${reasons.join(', ')}')}');
  }
  _verdict(conf.accepted);

  // ── Step 3: HomographyProjector ───────────────────────────────────────────
  _stepBanner(3, 'HomographyProjector');
  print('     ${dim('matrix (3×3 synthetic warp):')}');
  for (final row in demoMatrix) {
    print('       ${row.map((v) => v.toStringAsFixed(5).padLeft(10)).join('  ')}');
  }
  print('');
  final projector = HomographyProjector(demoMatrix);
  final projectedButtons = demoButtons.entries.map((e) {
    return projector.projectButton(e.key, e.value);
  }).toList();

  for (final pb in projectedButtons) {
    final isActive = pb.buttonId == activeButton;
    final tag = isActive ? cyan(' ← active') : '';
    print('     ${isActive ? bold(pb.buttonId) : dim(pb.buttonId)}$tag');
    for (var i = 0; i < pb.polygon.length; i++) {
      final p = pb.polygon[i];
      print('       corner[$i]: (${p.x.toStringAsFixed(2)}, ${p.y.toStringAsFixed(2)})');
    }
  }

  // ── Step 4: OpticalFlowTracker ────────────────────────────────────────────
  _stepBanner(4, 'OpticalFlowTracker');
  _field('stable input', stable ? 'true' : 'false', pass: stable);
  final tracker = OpticalFlowTracker();
  final tracked = tracker.updateAfterMotion(conf, stable: stable);
  _field('output.accepted', tracked.accepted ? 'true' : 'false', pass: tracked.accepted);
  if (!stable) {
    print('     ${warn('↳ motion detected — confidence zeroed')}');
    _field('output.matchScore', tracked.matchScore.toStringAsFixed(4));
    _field('output.reprojError', tracked.reprojectionError.isInfinite ? '∞' : tracked.reprojectionError.toStringAsFixed(2));
  } else {
    print('     ${dim('↳ stable — confidence unchanged from step 2')}');
  }

  // ── Step 5: TrackingConfidenceMonitor ─────────────────────────────────────
  _stepBanner(5, 'TrackingConfidenceMonitor');
  final monitor = TrackingConfidenceMonitor();
  final shouldStop = monitor.shouldStopHighlight(tracked);
  _field('shouldStopHighlight', shouldStop ? 'true' : 'false', pass: !shouldStop);
  if (shouldStop) {
    print('     ${warn('↳ highlight suppressed')}');
  }

  // ── Step 6: TrackingResetController ───────────────────────────────────────
  _stepBanner(6, 'TrackingResetController');
  final reset = TrackingResetController();
  _field('resetRequested', reset.resetRequested ? 'true' : 'false', pass: !reset.resetRequested);
  print('     ${dim('(no reset triggered in this run)')}');

  // ── Step 7: OverlayRenderer ───────────────────────────────────────────────
  _stepBanner(7, 'OverlayRenderer');
  final renderer = const OverlayRenderer();
  _field('activeButtonId', '"$activeButton"');
  _field('canShowHighlight', tracked.canShowHighlight ? 'true' : 'false', pass: tracked.canShowHighlight);
  final visible = renderer.visibleHighlights(
    confidence: tracked,
    projectedButtons: projectedButtons,
    activeButtonId: activeButton,
  );
  if (visible.isEmpty) {
    _field('visibleHighlights', '[] (empty)', pass: false);
    if (!tracked.canShowHighlight) {
      print('     ${warn('↳ no highlights: confidence rejected or motion detected')}');
    } else {
      print('     ${warn('↳ no highlights: "$activeButton" not found in projected buttons')}');
    }
  } else {
    _field('visibleHighlights', '[${visible.map((b) => b.buttonId).join(', ')}]', pass: true);
    for (final b in visible) {
      print('     ${ok('→')} ${b.buttonId}: ${b.polygon.length} corners projected onto frame');
    }
  }

  // ── Summary ───────────────────────────────────────────────────────────────
  print('');
  _rule();
  print('$_bold  Pipeline Summary$_reset');
  _rule();

  final steps = <String, bool>{
    'BrandMatcher': brandMatch != null,
    'MatchConfidenceState': conf.accepted,
    'HomographyProjector': true,
    'OpticalFlowTracker': tracked.accepted,
    'TrackingConfidenceMonitor': !shouldStop,
    'TrackingResetController': !reset.resetRequested,
    'OverlayRenderer': visible.isNotEmpty,
  };

  for (final e in steps.entries) {
    final icon = e.value ? ok('  ✓') : fail('  ✗');
    print('$icon  ${e.key.padRight(28)} ${e.value ? ok('PASS') : fail('FAIL')}');
  }

  final allPass = steps.values.every((v) => v);
  print('');
  print(allPass
      ? '  ${_bgGreen}${_white}${_bold}  ALL STEPS PASSED  $_reset'
      : '  ${_bgRed}${_white}${_bold}  PIPELINE HAS FAILURES  $_reset');
  print('');
}

// ── Sweep mode ────────────────────────────────────────────────────────────────
void _runSweep() {
  _header('Confidence Score Sweep  (inliers × reprojError)');
  print(dim('  Threshold: inliers≥4, ratio≥0.5, reproj≤5px'));
  print(dim('  Score formula: (inlierRatio) × (1 - reproj/50)'));
  print('');

  const totalKeypoints = 16;
  final inlierRange = [2, 3, 4, 6, 8, 10, 12, 14, 16];
  final reprojRange = [0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 12.0];

  // Header row
  final header = StringBuffer('     inliers╲reproj ');
  for (final r in reprojRange) {
    header.write(r.toStringAsFixed(1).padLeft(6));
  }
  print(bold(header.toString()));
  _rule();

  for (final inl in inlierRange) {
    final row = StringBuffer();
    row.write('     ${inl.toString().padLeft(3)} (${(inl / totalKeypoints).toStringAsFixed(2)})  ');
    for (final r in reprojRange) {
      final c = MatchConfidenceState.score(
        inlierCount: inl,
        totalKeypoints: totalKeypoints,
        reprojectionError: r,
      );
      final cell = c.matchScore.toStringAsFixed(2).padLeft(6);
      row.write(c.accepted ? ok(cell) : fail(cell));
    }
    print(row.toString());
  }

  print('');
  print(dim('  Green = accepted, Red = rejected'));
  print(dim('  Value = matchScore [0.0–1.0]'));
  print('');

  // Show exact boundaries
  print(bold('  Rejection boundaries:'));
  print('    ${fail('✗')} inliers < 4           → rejected regardless of ratio/reproj');
  print('    ${fail('✗')} inlierRatio < 0.5     → rejected (e.g. <8 inliers / 16 total)');
  print('    ${fail('✗')} reprojError > 5.0px   → rejected regardless of inlier count');
  print('    ${ok('✓')} ALL three pass        → accepted, score ∈ (0.0, 1.0]');
  print('');
}

// ── Args parser ───────────────────────────────────────────────────────────────
Map<String, String> _parseArgs(List<String> args) {
  final opts = <String, String>{
    'brand': 'panasonic',
    'inliers': '8',
    'keypoints': '12',
    'reproj': '2.3',
    'stable': 'true',
    'active': 'btn_power',
    'sweep': 'false',
    'help': 'false',
  };
  for (final arg in args) {
    if (arg == '--sweep') { opts['sweep'] = 'true'; continue; }
    if (arg == '--help' || arg == '-h') { opts['help'] = 'true'; continue; }
    if (arg.startsWith('--')) {
      final parts = arg.substring(2).split('=');
      if (parts.length == 2) opts[parts[0]] = parts[1];
    }
  }
  return opts;
}

void _printHelp() {
  _header('Vision Pipeline Debugger — Help');
  print('''
  ${bold('USAGE')}
    dart run debug/vision_pipeline_debugger.dart [options]

  ${bold('OPTIONS')}
    --brand=<name>      brand label            (default: panasonic)
    --inliers=<n>       inlier keypoint count  (default: 8)
    --keypoints=<n>     total keypoints        (default: 12)
    --reproj=<f>        reprojection error px  (default: 2.3)
    --stable=<bool>     optical flow stable?   (default: true)
    --active=<id>       active button to show  (default: btn_power)
    --sweep             show accept/reject grid across param ranges
    --help              show this message

  ${bold('EXAMPLES')}
    # Default run (should PASS all steps)
    dart run debug/vision_pipeline_debugger.dart

    # Trigger rejection: too few inliers
    dart run debug/vision_pipeline_debugger.dart --inliers=2 --keypoints=12

    # Trigger rejection: high reprojection error
    dart run debug/vision_pipeline_debugger.dart --reproj=7.5

    # Trigger optical flow reset (unstable motion)
    dart run debug/vision_pipeline_debugger.dart --stable=false

    # Show full confidence score sweep grid
    dart run debug/vision_pipeline_debugger.dart --sweep
''');
}
