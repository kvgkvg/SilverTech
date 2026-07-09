import 'package:flutter/foundation.dart' show Uint8List, kIsWeb;

import '../guidance/guidance_client.dart';
import '../submissions/submission_client.dart';
import '../templates/template_repository_client.dart';
import '../vision/logo_anchor_client.dart';
import '../vision/vision_log_client.dart';

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

  /// Real recognition: the frame goes to `/api/vision/logo-anchor`, which
  /// names the brand, picks the template, and projects button quads.
  Future<BackendRecognitionResult> recognizeFromFrame(Uint8List frameBytes);

  Future<GuidanceOutputDto> createGuidance({
    required String templateId,
    required String userQueryText,
  });

  /// Upload the panel photo, then file the proposed labels for admin review.
  /// Returns the submission id.
  Future<String> submitTemplate({
    required Uint8List imageBytes,
    required String brand,
    required String applianceType,
    required Map<String, Object?> Function(String imageUrl) buildLabels,
  });
}

class BackendRecognitionResult {
  const BackendRecognitionResult({
    required this.template,
    required this.matchScore,
    this.tier,
    this.brand,
    this.projectedButtons = const {},
    this.logoFrameBox,
  });

  final TemplateDetailDto template;
  final double matchScore;

  /// HOMOGRAPHY_REFINED | LOGO_SIMILARITY | null (scripted demo path).
  final String? tier;
  final String? brand;

  /// button_id -> 4 corners in frame pixel coordinates.
  final Map<String, List<ProjectedPoint>> projectedButtons;

  /// Brand logo's box in frame pixel coordinates, when the pose was detected.
  final LogoFrameBox? logoFrameBox;
}

class HttpSilverBackendGateway implements SilverBackendGateway {
  HttpSilverBackendGateway({
    TemplateRepositoryClient? templates,
    GuidanceClient? guidance,
    VisionLogClient? visionLogs,
    LogoAnchorClient? logoAnchor,
    SubmissionClient? submissions,
  })  : _templates = templates ??
            TemplateRepositoryClient(baseUrl: defaultSilverTechApiBaseUrl),
        _guidance =
            guidance ?? GuidanceClient(baseUrl: defaultSilverTechApiBaseUrl),
        _visionLogs =
            visionLogs ?? VisionLogClient(baseUrl: defaultSilverTechApiBaseUrl),
        _logoAnchor = logoAnchor ??
            LogoAnchorClient(baseUrl: defaultSilverTechApiBaseUrl),
        _submissions = submissions ??
            SubmissionClient(baseUrl: defaultSilverTechApiBaseUrl);

  final TemplateRepositoryClient _templates;
  final GuidanceClient _guidance;
  final VisionLogClient _visionLogs;
  final LogoAnchorClient _logoAnchor;
  final SubmissionClient _submissions;

  @override
  Future<String> submitTemplate({
    required Uint8List imageBytes,
    required String brand,
    required String applianceType,
    required Map<String, Object?> Function(String imageUrl) buildLabels,
  }) async {
    final String imageUrl =
        await _submissions.uploadImage(imageBytes: imageBytes);
    return _submissions.createSubmission(
      brand: brand,
      applianceType: applianceType,
      imageUrl: imageUrl,
      proposedLabels: buildLabels(imageUrl),
    );
  }

  @override
  Future<BackendRecognitionResult> recognizeFromFrame(
      Uint8List frameBytes) async {
    final result = await _logoAnchor.match(frameBytes: frameBytes);
    final template = await _templates.fetchTemplate(result.templateId);
    try {
      await _visionLogs.write(
        templateId: template.id,
        brandCandidate: result.brand ?? template.brand,
        matchScore: result.matchScore,
        accepted: result.accepted,
      );
    } catch (_) {
      // Recognition should not fail just because telemetry is unavailable.
    }
    return BackendRecognitionResult(
      template: template,
      matchScore: result.matchScore,
      tier: result.tier,
      brand: result.brand,
      projectedButtons: result.projectedButtons,
      logoFrameBox: result.logoFrameBox,
    );
  }

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
}
