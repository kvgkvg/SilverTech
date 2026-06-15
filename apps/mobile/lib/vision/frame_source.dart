import 'dart:typed_data';

/// Source of camera frames for the detection loop. Implementations grab the
/// current frame as JPEG bytes.
abstract class FrameSource {
  Future<void> start();
  Future<Uint8List> grabFrame();
  Future<void> stop();
}
