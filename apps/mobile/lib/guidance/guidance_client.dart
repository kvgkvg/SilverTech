class GuidanceClient {
  const GuidanceClient({required this.baseUrl});
  final String baseUrl;
  Uri get queryUri => Uri.parse('$baseUrl/api/query');
}
