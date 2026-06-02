import 'geometry.dart';

class HomographyProjector {
  const HomographyProjector(this.matrix);

  final List<List<double>> matrix;

  Point2 project(Point2 point) {
    final x = point.x;
    final y = point.y;
    final w = matrix[2][0] * x + matrix[2][1] * y + matrix[2][2];
    return Point2(
      (matrix[0][0] * x + matrix[0][1] * y + matrix[0][2]) / w,
      (matrix[1][0] * x + matrix[1][1] * y + matrix[1][2]) / w,
    );
  }

  ProjectedButton projectButton(String buttonId, BBox bbox) {
    return ProjectedButton(
      buttonId: buttonId,
      polygon: bbox.corners().map(project).toList(),
    );
  }
}
