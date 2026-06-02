class STTClient {
  const STTClient({required this.baseUrl});
  final String baseUrl;
  Uri get uri => Uri.parse('$baseUrl/api/stt');
}
