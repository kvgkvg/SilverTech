class TemplateRepositoryClient {
  const TemplateRepositoryClient({required this.baseUrl});
  final String baseUrl;

  Uri candidatesUri() => Uri.parse('$baseUrl/api/vision/candidates');
  Uri templateUri(String templateId) =>
      Uri.parse('$baseUrl/api/templates/$templateId');
}
