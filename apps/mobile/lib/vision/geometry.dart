class Point2 {
  const Point2(this.x, this.y);
  final double x;
  final double y;
}

class BBox {
  const BBox({
    required this.x,
    required this.y,
    required this.width,
    required this.height,
  });
  final double x;
  final double y;
  final double width;
  final double height;

  List<Point2> corners() => <Point2>[
        Point2(x, y),
        Point2(x + width, y),
        Point2(x + width, y + height),
        Point2(x, y + height),
      ];
}

class ProjectedButton {
  const ProjectedButton({required this.buttonId, required this.polygon});
  final String buttonId;
  final List<Point2> polygon;
}
