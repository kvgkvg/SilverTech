import 'geometry.dart';

/// Utility for projecting 2D coordinates using a 3x3 homography matrix.
class HomographyProjector {
  /// Creates a HomographyProjector with a 3x3 projection matrix.
  const HomographyProjector(this.matrix);

  /// The 3x3 homography projection matrix.
  final List<List<double>> matrix;

  /// Projects a single [point] (x, y) into perspective space.
  ///
  /// Performs matrix multiplication and returns a [Point2] after perspective division.
  Point2 project(Point2 point) {
    final x = point.x;
    final y = point.y;
    final w = matrix[2][0] * x + matrix[2][1] * y + matrix[2][2];
    return Point2(
      (matrix[0][0] * x + matrix[0][1] * y + matrix[0][2]) / w,
      (matrix[1][0] * x + matrix[1][1] * y + matrix[1][2]) / w,
    );
  }

  /// Projects the 4 corners of a button's [bbox] into the frame perspective space.
  ///
  /// Takes a [buttonId] and [bbox], projects each corner, and returns the [ProjectedButton] quad.
  ProjectedButton projectButton(String buttonId, BBox bbox) {
    return ProjectedButton(
      buttonId: buttonId,
      polygon: bbox.corners().map(project).toList(),
    );
  }
}
