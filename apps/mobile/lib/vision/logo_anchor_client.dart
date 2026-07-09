import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

/// Client for `POST /api/vision/logo-anchor`: sends a camera frame, receives
/// the matched template id plus button quads projected into frame coordinates.
class LogoAnchorClient {
  LogoAnchorClient({
    required this.baseUrl,
    http.Client? httpClient,
  }) : _httpClient = httpClient ?? http.Client();

  final String baseUrl;
  final http.Client _httpClient;

  Uri logoAnchorUri() => Uri.parse('$baseUrl/api/vision/logo-anchor');

  /// [templateId] null lets the server auto-detect (brand-first flow).
  Future<LogoAnchorResultDto> match({
    required Uint8List frameBytes,
    String? templateId,
  }) async {
    final request = http.MultipartRequest('POST', logoAnchorUri());
    if (templateId != null) {
      request.fields['template_id'] = templateId;
    }
    request.files.add(http.MultipartFile.fromBytes(
      'frame',
      frameBytes,
      filename: 'frame.jpg',
    ));
    final streamed = await _httpClient.send(request);
    final response = await http.Response.fromStream(streamed);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      String detail = 'logo-anchor failed (${response.statusCode})';
      try {
        final body = jsonDecode(response.body) as Map<String, Object?>;
        detail = body['detail'] as String? ?? detail;
      } catch (_) {}
      throw LogoAnchorException(statusCode: response.statusCode, detail: detail);
    }
    return LogoAnchorResultDto.fromJson(
      jsonDecode(response.body) as Map<String, Object?>,
    );
  }
}

class LogoAnchorException implements Exception {
  const LogoAnchorException({required this.statusCode, required this.detail});

  final int statusCode;
  final String detail;

  @override
  String toString() => 'LogoAnchorException($statusCode): $detail';
}

class LogoAnchorResultDto {
  const LogoAnchorResultDto({
    required this.templateId,
    required this.accepted,
    required this.tier,
    required this.matchScore,
    required this.brand,
    required this.projectedButtons,
  });

  factory LogoAnchorResultDto.fromJson(Map<String, Object?> json) {
    final rawButtons =
        json['projected_buttons'] as Map<String, Object?>? ?? const {};
    final buttons = <String, List<ProjectedPoint>>{};
    rawButtons.forEach((buttonId, quad) {
      buttons[buttonId] = (quad as List<Object?>)
          .map((p) => ProjectedPoint.fromJson(p as List<Object?>))
          .toList();
    });
    return LogoAnchorResultDto(
      templateId: json['template_id'] as String,
      accepted: json['accepted'] as bool? ?? false,
      tier: json['tier'] as String? ?? 'REJECTED',
      matchScore: (json['match_score'] as num?)?.toDouble() ?? 0.0,
      brand: json['brand'] as String?,
      projectedButtons: buttons,
    );
  }

  final String templateId;
  final bool accepted;
  final String tier;
  final double matchScore;
  final String? brand;

  /// button_id -> 4 corner points in frame pixel coordinates.
  final Map<String, List<ProjectedPoint>> projectedButtons;
}

class ProjectedPoint {
  const ProjectedPoint(this.x, this.y);

  factory ProjectedPoint.fromJson(List<Object?> json) => ProjectedPoint(
        (json[0] as num).toDouble(),
        (json[1] as num).toDouble(),
      );

  final double x;
  final double y;
}
