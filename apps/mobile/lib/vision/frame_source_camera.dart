import 'dart:typed_data';

import 'package:camera/camera.dart';

import 'frame_source.dart';

/// Frame source backed by the `camera` plugin. Works on web (camera_web) and
/// mobile via takePicture(); the `camera` plugin has no Linux implementation,
/// so [createFrameSource] falls back to [FileFrameSource] there.
class CameraFrameSource implements FrameSource {
  CameraFrameSource._(this.controller);

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
    try {
      await controller.initialize();
    } catch (_) {
      await controller.dispose();
      rethrow;
    }
    return CameraFrameSource._(controller);
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
  // Terminal: disposes the controller. A stopped source cannot be restarted;
  // create a new one via [open] / createFrameSource() for a fresh session.
  Future<void> stop() async {
    await controller.dispose();
  }
}
