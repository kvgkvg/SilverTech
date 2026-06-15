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
