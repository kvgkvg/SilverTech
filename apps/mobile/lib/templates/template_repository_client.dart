import 'dart:convert';

import 'package:http/http.dart' as http;

import '../backend/api_http_client.dart';

class TemplateRepositoryClient {
  TemplateRepositoryClient({
    required this.baseUrl,
    http.Client? httpClient,
  }) : _httpClient = httpClient ?? ApiHttpClient();

  final String baseUrl;
  final http.Client _httpClient;

  Uri candidatesUri() => Uri.parse('$baseUrl/api/vision/candidates');
  Uri templateUri(String templateId) =>
      Uri.parse('$baseUrl/api/templates/$templateId');

  Future<List<TemplateSummaryDto>> findCandidates({
    String? brand,
    String? applianceType,
    double? brandConfidence,
  }) async {
    final response = await _httpClient.post(
      candidatesUri(),
      headers: const <String, String>{'Content-Type': 'application/json'},
      body: jsonEncode(<String, Object?>{
        'brand': brand,
        'appliance_type': applianceType,
        'brand_confidence': brandConfidence,
      }),
    );
    _throwIfError(response);
    final body = jsonDecode(response.body) as Map<String, Object?>;
    final candidates = body['candidates'] as List<Object?>;
    return candidates
        .cast<Map<String, Object?>>()
        .map(TemplateSummaryDto.fromJson)
        .toList();
  }

  Future<TemplateDetailDto> fetchTemplate(String templateId) async {
    final response = await _httpClient.get(templateUri(templateId));
    _throwIfError(response);
    return TemplateDetailDto.fromJson(
      jsonDecode(response.body) as Map<String, Object?>,
    );
  }
}

void _throwIfError(http.Response response) {
  if (response.statusCode >= 200 && response.statusCode < 300) {
    return;
  }
  final body = jsonDecode(response.body) as Map<String, Object?>;
  final detail = body['detail'];
  if (detail is Map<String, Object?>) {
    throw FriendlyBackendException(
      messageVi: detail['message_vi'] as String? ?? 'Co loi xay ra.',
      recoveryAction: detail['recovery_action'] as String? ?? 'try_again',
      statusCode: response.statusCode,
    );
  }
  throw FriendlyBackendException(
    messageVi: body['message_vi'] as String? ?? 'Co loi xay ra.',
    recoveryAction: body['recovery_action'] as String? ?? 'try_again',
    statusCode: response.statusCode,
  );
}

class FriendlyBackendException implements Exception {
  const FriendlyBackendException({
    required this.messageVi,
    required this.recoveryAction,
    required this.statusCode,
  });

  final String messageVi;
  final String recoveryAction;
  final int statusCode;

  @override
  String toString() {
    return 'FriendlyBackendException(statusCode: $statusCode, '
        'recoveryAction: $recoveryAction, messageVi: $messageVi)';
  }
}

class TemplateSummaryDto {
  const TemplateSummaryDto({
    required this.id,
    required this.brand,
    required this.applianceType,
    required this.templateCode,
    required this.version,
    required this.status,
    required this.templateImageUrl,
  });

  factory TemplateSummaryDto.fromJson(Map<String, Object?> json) {
    return TemplateSummaryDto(
      id: json['id'] as String,
      brand: json['brand'] as String,
      applianceType: json['appliance_type'] as String,
      templateCode: json['template_code'] as String,
      version: json['version'] as int,
      status: json['status'] as String,
      templateImageUrl: json['template_image_url'] as String,
    );
  }

  final String id;
  final String brand;
  final String applianceType;
  final String templateCode;
  final int version;
  final String status;
  final String templateImageUrl;

  @override
  String toString() {
    return 'TemplateSummaryDto(id: $id, brand: $brand, '
        'applianceType: $applianceType, version: $version, status: $status)';
  }
}

class TemplateDetailDto {
  const TemplateDetailDto({
    required this.id,
    required this.brand,
    required this.applianceType,
    required this.templateCode,
    required this.version,
    required this.status,
    required this.templateImageUrl,
    required this.buttons,
  });

  factory TemplateDetailDto.fromJson(Map<String, Object?> json) {
    final buttons = json['buttons'] as List<Object?>;
    return TemplateDetailDto(
      id: json['id'] as String,
      brand: json['brand'] as String,
      applianceType: json['appliance_type'] as String,
      templateCode: json['template_code'] as String,
      version: json['version'] as int,
      status: json['status'] as String,
      templateImageUrl: json['template_image_url'] as String,
      buttons: buttons
          .cast<Map<String, Object?>>()
          .map(TemplateButtonDto.fromJson)
          .toList(),
    );
  }

  final String id;
  final String brand;
  final String applianceType;
  final String templateCode;
  final int version;
  final String status;
  final String templateImageUrl;
  final List<TemplateButtonDto> buttons;

  @override
  String toString() {
    return 'TemplateDetailDto(id: $id, brand: $brand, '
        'applianceType: $applianceType, version: $version, '
        'status: $status, buttons: ${buttons.length})';
  }
}

class TemplateButtonDto {
  const TemplateButtonDto({
    required this.buttonId,
    required this.label,
    required this.vietnameseName,
    required this.functionDescription,
    required this.bbox,
    required this.buttonType,
  });

  factory TemplateButtonDto.fromJson(Map<String, Object?> json) {
    return TemplateButtonDto(
      buttonId: json['button_id'] as String,
      label: json['label'] as String,
      vietnameseName: json['vietnamese_name'] as String,
      functionDescription: json['function_description'] as String,
      bbox: TemplateBBoxDto.fromJson(
        json['bbox_template_coordinates'] as Map<String, Object?>,
      ),
      buttonType: json['button_type'] as String,
    );
  }

  final String buttonId;
  final String label;
  final String vietnameseName;
  final String functionDescription;
  final TemplateBBoxDto bbox;
  final String buttonType;

  @override
  String toString() {
    return 'TemplateButtonDto(buttonId: $buttonId, label: $label, '
        'buttonType: $buttonType)';
  }
}

class TemplateBBoxDto {
  const TemplateBBoxDto({
    required this.x,
    required this.y,
    required this.width,
    required this.height,
  });

  factory TemplateBBoxDto.fromJson(Map<String, Object?> json) {
    return TemplateBBoxDto(
      x: (json['x'] as num).toDouble(),
      y: (json['y'] as num).toDouble(),
      width: (json['width'] as num).toDouble(),
      height: (json['height'] as num).toDouble(),
    );
  }

  final double x;
  final double y;
  final double width;
  final double height;

  @override
  String toString() {
    return 'TemplateBBoxDto(x: $x, y: $y, width: $width, height: $height)';
  }
}
