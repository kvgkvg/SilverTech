import 'package:http/http.dart' as http;

/// ngrok's free tier answers any request with a browser `User-Agent` with an
/// HTML warning page instead of the real response. A request carrying this
/// header is served normally, so every backend call has to send it.
const Map<String, String> apiRequestHeaders = <String, String>{
  'ngrok-skip-browser-warning': '1',
};

/// An [http.Client] that stamps [apiRequestHeaders] onto every request.
///
/// Wrapping at the client level rather than the call site also covers
/// `MultipartRequest`, which the frame-upload paths send through [send].
class ApiHttpClient extends http.BaseClient {
  ApiHttpClient([http.Client? inner]) : _inner = inner ?? http.Client();

  final http.Client _inner;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) {
    request.headers.addAll(apiRequestHeaders);
    return _inner.send(request);
  }

  @override
  void close() => _inner.close();
}
