class VisionLogClient {
  const VisionLogClient({required this.baseUrl});
  final String baseUrl;
  Uri get uri => Uri.parse('$baseUrl/api/vision/logs');
}
