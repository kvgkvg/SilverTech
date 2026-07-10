import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../backend/api_http_client.dart';
import '../templates/template_repository_client.dart';

class GuidanceClient {
  GuidanceClient({
    required this.baseUrl,
    this.timeout = const Duration(seconds: 60),
    http.Client? httpClient,
  }) : _httpClient = httpClient ?? ApiHttpClient();

  final String baseUrl;

  /// A real LLM answer takes 6-27s, and `package:http` has no default timeout,
  /// so without this the voice screen can spin forever on a stalled network.
  final Duration timeout;

  final http.Client _httpClient;

  Uri get queryUri => Uri.parse('$baseUrl/api/query');

  Future<GuidanceOutputDto> createGuidance({
    required String templateId,
    required String userQueryText,
  }) async {
    final http.Response response;
    try {
      response = await _httpClient
          .post(
            queryUri,
            headers: const <String, String>{'Content-Type': 'application/json'},
            body: jsonEncode(<String, Object?>{
              'template_id': templateId,
              'user_query_text': userQueryText,
            }),
          )
          .timeout(timeout);
    } on TimeoutException {
      throw const FriendlyBackendException(
        messageVi: 'Mạng chậm quá. Vui lòng thử lại.',
        recoveryAction: 'try_again',
        statusCode: 504,
      );
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      final body = jsonDecode(response.body) as Map<String, Object?>;
      throw FriendlyBackendException(
        messageVi: body['message_vi'] as String? ?? 'Co loi xay ra.',
        recoveryAction: body['recovery_action'] as String? ?? 'try_again',
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

  @override
  String toString() {
    return 'GuidanceOutputDto(intent: $intent, steps: ${steps.length}, '
        'safetyNote: $safetyNote)';
  }
}

class GuidanceStepDto {
  const GuidanceStepDto({
    required this.stepNumber,
    required this.instructionVi,
    required this.buttonId,
    required this.expectedResult,
    this.audioUrl,
  });

  factory GuidanceStepDto.fromJson(Map<String, Object?> json) {
    return GuidanceStepDto(
      stepNumber: json['step_number'] as int,
      instructionVi: json['instruction_vi'] as String,
      buttonId: json['button_id'] as String,
      expectedResult: json['expected_result'] as String,
      audioUrl: json['audio_url'] as String?,
    );
  }

  final int stepNumber;
  final String instructionVi;
  final String buttonId;
  final String expectedResult;
  final String? audioUrl;

  @override
  String toString() {
    return 'GuidanceStepDto(stepNumber: $stepNumber, buttonId: $buttonId, '
        'instructionVi: $instructionVi)';
  }
}
