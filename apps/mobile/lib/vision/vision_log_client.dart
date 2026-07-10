import 'dart:convert';

import 'package:http/http.dart' as http;

import '../backend/api_http_client.dart';

class VisionLogClient {
  VisionLogClient({required this.baseUrl, http.Client? httpClient})
      : _httpClient = httpClient ?? ApiHttpClient();

  final String baseUrl;
  final http.Client _httpClient;

  Uri get uri => Uri.parse('$baseUrl/api/vision/logs');

  Future<void> write({
    String? templateId,
    String? brandCandidate,
    double? matchScore,
    int? inlierCount,
    double? inlierRatio,
    double? reprojectionError,
    required bool accepted,
    String? failureReason,
  }) async {
    await _httpClient.post(
      uri,
      headers: const <String, String>{'Content-Type': 'application/json'},
      body: jsonEncode(<String, Object?>{
        'template_id': templateId,
        'brand_candidate': brandCandidate,
        'match_score': matchScore,
        'inlier_count': inlierCount,
        'inlier_ratio': inlierRatio,
        'reprojection_error': reprojectionError,
        'accepted': accepted,
        'failure_reason': failureReason,
      }),
    );
  }
}
