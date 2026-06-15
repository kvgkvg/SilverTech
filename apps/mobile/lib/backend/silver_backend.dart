import 'dart:typed_data';

import 'package:flutter/foundation.dart' show kIsWeb;

import '../guidance/guidance_client.dart';
import '../templates/template_repository_client.dart';
import '../vision/vision_log_client.dart';
import '../vision/vision_match_client.dart';

const String _apiBaseUrlOverride =
    String.fromEnvironment('SILVERTECH_API_BASE_URL');

/// Base URL resolution:
/// 1. `--dart-define=SILVERTECH_API_BASE_URL=...` wins if provided.
/// 2. Web (Chrome demo) talks to the API on `localhost`.
/// 3. Native/emulator keeps `10.0.2.2` (Android host loopback).
String get defaultSilverTechApiBaseUrl {
  if (_apiBaseUrlOverride.isNotEmpty) return _apiBaseUrlOverride;
  return kIsWeb ? 'http://localhost:8000' : 'http://10.0.2.2:8000';
}
const String demoTemplateId = 'template_panasonic_microwave_nn_gt35hm_v1';

abstract class SilverBackendGateway {
  Future<BackendRecognitionResult> recognizeDefault();

  Future<GuidanceOutputDto> createGuidance({
    required String templateId,
    required String userQueryText,
  });

  Future<VisionMatchResult> match(
    Uint8List frame, {
    String? brand,
    String? applianceType,
  });

  Future<TemplateDetailDto> fetchTemplate(String templateId);
}

class BackendRecognitionResult {
  const BackendRecognitionResult({
    required this.template,
    required this.matchScore,
  });

  final TemplateDetailDto template;
  final double matchScore;
}

class HttpSilverBackendGateway implements SilverBackendGateway {
  HttpSilverBackendGateway({
    TemplateRepositoryClient? templates,
    GuidanceClient? guidance,
    VisionLogClient? visionLogs,
    VisionMatchClient? visionMatch,
  })  : _templates = templates ??
            TemplateRepositoryClient(baseUrl: defaultSilverTechApiBaseUrl),
        _guidance =
            guidance ?? GuidanceClient(baseUrl: defaultSilverTechApiBaseUrl),
        _visionLogs =
            visionLogs ?? VisionLogClient(baseUrl: defaultSilverTechApiBaseUrl),
        _visionMatch =
            visionMatch ?? VisionMatchClient(baseUrl: defaultSilverTechApiBaseUrl);

  final TemplateRepositoryClient _templates;
  final GuidanceClient _guidance;
  final VisionLogClient _visionLogs;
  final VisionMatchClient _visionMatch;

  @override
  Future<BackendRecognitionResult> recognizeDefault() async {
    const double candidateConfidence = 0.94;
    final template = await _templates.fetchTemplate(demoTemplateId);
    try {
      await _visionLogs.write(
        templateId: template.id,
        brandCandidate: template.brand,
        matchScore: candidateConfidence,
        accepted: true,
      );
    } catch (_) {
      // Demo navigation should not fail just because telemetry is unavailable.
    }
    return BackendRecognitionResult(
      template: template,
      matchScore: candidateConfidence,
    );
  }

  @override
  Future<GuidanceOutputDto> createGuidance({
    required String templateId,
    required String userQueryText,
  }) {
    return _guidance.createGuidance(
      templateId: templateId,
      userQueryText: userQueryText,
    );
  }

  @override
  Future<VisionMatchResult> match(
    Uint8List frame, {
    String? brand,
    String? applianceType,
  }) {
    return _visionMatch.match(frame, brand: brand, applianceType: applianceType);
  }

  @override
  Future<TemplateDetailDto> fetchTemplate(String templateId) {
    return _templates.fetchTemplate(templateId);
  }
}
