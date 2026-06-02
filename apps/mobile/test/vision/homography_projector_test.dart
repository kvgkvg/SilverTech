import 'package:silvertech_mobile/vision/geometry.dart';
import 'package:silvertech_mobile/vision/homography_projector.dart';

void main() {
  const projector = HomographyProjector(<List<double>>[
    <double>[1, 0, 10],
    <double>[0, 1, 20],
    <double>[0, 0, 1],
  ]);

  final projected = projector.projectButton(
    'quick_wash',
    const BBox(x: 210, y: 145, width: 85, height: 50),
  );

  assert(projected.buttonId == 'quick_wash');
  assert(projected.polygon.first.x == 220);
  assert(projected.polygon.first.y == 165);
  assert(projected.polygon[2].x == 305);
  assert(projected.polygon[2].y == 215);
}
