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
