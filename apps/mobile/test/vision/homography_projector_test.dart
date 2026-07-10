// Author: Luu Thuong Hong (MSSV: 23122006) - Homography Camera Matrix Projection Test
import 'package:flutter_test/flutter_test.dart';
import 'package:silvertech_mobile/vision/geometry.dart';
import 'package:silvertech_mobile/vision/homography_projector.dart';

void main() {
  test('projects template button coordinates through homography', () {
    const projector = HomographyProjector(<List<double>>[
      <double>[1, 0, 10],
      <double>[0, 1, 20],
      <double>[0, 0, 1],
    ]);

    final projected = projector.projectButton(
      'quick_wash',
      const BBox(x: 210, y: 145, width: 85, height: 50),
    );

    expect(projected.buttonId, 'quick_wash');
    expect(projected.polygon.first.x, 220);
    expect(projected.polygon.first.y, 165);
    expect(projected.polygon[2].x, 305);
    expect(projected.polygon[2].y, 215);
  });
}
