import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../backend/api_http_client.dart';
import '../templates/template_repository_client.dart' show FriendlyBackendException;

/// Client for the template submission workflow:
/// 1. [uploadImage] stores the panel photo and returns its image_url.
/// 2. [createSubmission] files the proposed labels for admin review.
class SubmissionClient {
  SubmissionClient({
    required this.baseUrl,
    http.Client? httpClient,
  }) : _httpClient = httpClient ?? ApiHttpClient();

  final String baseUrl;
  final http.Client _httpClient;

  Future<String> uploadImage({
    required Uint8List imageBytes,
    String filename = 'panel.jpg',
  }) async {
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('$baseUrl/api/submissions/image'),
    );
    request.files.add(http.MultipartFile.fromBytes(
      'image',
      imageBytes,
      filename: filename,
    ));
    final streamed = await _httpClient.send(request);
    final response = await http.Response.fromStream(streamed);
    final body = _decodeOrThrow(response);
    return body['image_url'] as String;
  }

  Future<String> createSubmission({
    required String brand,
    required String applianceType,
    required String imageUrl,
    required Map<String, Object?> proposedLabels,
    String? submittedBy,
  }) async {
    final response = await _httpClient.post(
      Uri.parse('$baseUrl/api/submissions'),
      headers: const <String, String>{'Content-Type': 'application/json'},
      body: jsonEncode(<String, Object?>{
        'submitted_by': submittedBy,
        'brand': brand,
        'appliance_type': applianceType,
        'image_url': imageUrl,
        'proposed_labels_json': proposedLabels,
      }),
    );
    final body = _decodeOrThrow(response);
    return body['submission_id'] as String;
  }

  Map<String, Object?> _decodeOrThrow(http.Response response) {
    Map<String, Object?>? body;
    try {
      body = jsonDecode(response.body) as Map<String, Object?>;
    } catch (_) {}
    if (response.statusCode < 200 || response.statusCode >= 300) {
      final detail = body?['detail'];
      final messageVi = detail is Map<String, Object?>
          ? detail['message_vi'] as String? ?? 'Có lỗi xảy ra.'
          : 'Có lỗi xảy ra.';
      throw FriendlyBackendException(
        messageVi: messageVi,
        recoveryAction: 'try_again',
        statusCode: response.statusCode,
      );
    }
    return body ?? const <String, Object?>{};
  }
}
