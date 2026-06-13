import 'dart:convert';

import 'package:http/http.dart' as http;

import '../templates/template_repository_client.dart';

class GuidanceClient {
  GuidanceClient({
    required this.baseUrl,
    http.Client? httpClient,
  }) : _httpClient = httpClient ?? http.Client();

  final String baseUrl;
  final http.Client _httpClient;

  Uri get queryUri => Uri.parse('$baseUrl/api/query');

  Future<GuidanceOutputDto> createGuidance({
    required String templateId,
    required String userQueryText,
  }) async {
    final response = await _httpClient.post(
      queryUri,
      headers: const <String, String>{'Content-Type': 'application/json'},
      body: jsonEncode(<String, Object?>{
        'template_id': templateId,
        'user_query_text': userQueryText,
      }),
    );
    if (response.statusCode < 200 || response.statusCode >= 300) {
      final decoded = jsonDecode(response.body);
      Map<String, Object?> payload;
      if (decoded is Map<String, Object?> &&
          decoded['detail'] is Map<String, Object?>) {
        payload = decoded['detail'] as Map<String, Object?>;
      } else if (decoded is Map<String, Object?>) {
        payload = decoded;
      } else {
        payload = const <String, Object?>{};
      }
      throw FriendlyBackendException(
        messageVi: payload['message_vi'] as String? ?? 'Co loi xay ra.',
        recoveryAction: payload['recovery_action'] as String? ?? 'try_again',
        statusCode: response.statusCode,
      );
    }
    return GuidanceOutputDto.fromJson(
      jsonDecode(response.body) as Map<String, Object?>,
    );
  }
}

class GuidanceOutputDto {
  const GuidanceOutputDto({
    required this.intent,
    required this.steps,
    this.safetyNote,
  });

  factory GuidanceOutputDto.fromJson(Map<String, Object?> json) {
    final steps = json['steps'] as List<Object?>;
    return GuidanceOutputDto(
      intent: json['intent'] as String,
      steps: steps
          .cast<Map<String, Object?>>()
          .map(GuidanceStepDto.fromJson)
          .toList(),
      safetyNote: json['safety_note'] as String?,
    );
  }

  final String intent;
  final List<GuidanceStepDto> steps;
  final String? safetyNote;
}

class GuidanceStepDto {
  const GuidanceStepDto({
    required this.stepNumber,
    required this.instructionVi,
    required this.buttonId,
    required this.expectedResult,
  });

  factory GuidanceStepDto.fromJson(Map<String, Object?> json) {
    return GuidanceStepDto(
      stepNumber: json['step_number'] as int,
      instructionVi: json['instruction_vi'] as String,
      buttonId: json['button_id'] as String,
      expectedResult: json['expected_result'] as String,
    );
  }

  final int stepNumber;
  final String instructionVi;
  final String buttonId;
  final String expectedResult;
}
