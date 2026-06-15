import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../templates/template_repository_client.dart'
    show FriendlyBackendException;
import 'geometry.dart';

class VisionMatchResult {
  const VisionMatchResult({
    required this.accepted,
    this.templateId,
    this.matchScore,
    this.failureReason,
    this.projectedButtons = const <ProjectedButton>[],
  });

  final bool accepted;
  final String? templateId;
  final double? matchScore;
  final String? failureReason;
  final List<ProjectedButton> projectedButtons;

  factory VisionMatchResult.fromJson(Map<String, Object?> json) {
    final rawButtons =
        (json['projected_buttons'] as List<Object?>?) ?? const <Object?>[];
    return VisionMatchResult(
      accepted: json['accepted'] as bool? ?? false,
      templateId: json['template_id'] as String?,
      matchScore: (json['match_score'] as num?)?.toDouble(),
      failureReason: json['failure_reason'] as String?,
      projectedButtons: rawButtons
          .whereType<Map<String, Object?>>()
          .map(_buttonFromJson)
          .toList(),
    );
  }

  static ProjectedButton _buttonFromJson(Map<String, Object?> json) {
    final rawPolygon = (json['polygon'] as List<Object?>?) ?? const <Object?>[];
    return ProjectedButton(
      buttonId: json['button_id'] as String? ?? '',
      polygon: rawPolygon
          .whereType<Map<String, Object?>>()
          .map((p) =>
              Point2((p['x'] as num).toDouble(), (p['y'] as num).toDouble()))
          .toList(),
    );
  }
}

class VisionMatchClient {
  VisionMatchClient({required this.baseUrl, http.Client? httpClient})
      : _httpClient = httpClient ?? http.Client();

  final String baseUrl;
  final http.Client _httpClient;

  Uri get uri => Uri.parse('$baseUrl/api/vision/match');

  Future<VisionMatchResult> match(
    Uint8List jpegBytes, {
    String? brand,
    String? applianceType,
  }) async {
    final request = http.MultipartRequest('POST', uri);
    if (brand != null) request.fields['brand'] = brand;
    if (applianceType != null) request.fields['appliance_type'] = applianceType;
    request.files.add(
      http.MultipartFile.fromBytes('file', jpegBytes, filename: 'frame.jpg'),
    );

    final streamed = await _httpClient.send(request);
    final response = await http.Response.fromStream(streamed);

    if (response.statusCode < 200 || response.statusCode >= 300) {
      final decoded = jsonDecode(response.body);
      final detail = decoded is Map<String, Object?> &&
              decoded['detail'] is Map<String, Object?>
          ? decoded['detail'] as Map<String, Object?>
          : (decoded is Map<String, Object?>
              ? decoded
              : const <String, Object?>{});
      throw FriendlyBackendException(
        messageVi: detail['message_vi'] as String? ?? 'Khong nhan dien duoc.',
        recoveryAction: detail['recovery_action'] as String? ?? 'rescan',
        statusCode: response.statusCode,
      );
    }

    return VisionMatchResult.fromJson(
      jsonDecode(response.body) as Map<String, Object?>,
    );
  }
}
