import '../guidance/guidance_client.dart';
import '../templates/template_repository_client.dart';
import '../vision/vision_log_client.dart';

const String defaultSilverTechApiBaseUrl = String.fromEnvironment(
  'SILVERTECH_API_BASE_URL',
  defaultValue: 'http://10.0.2.2:8000',
);
const String demoTemplateId = 'template_panasonic_microwave_nn_gt35hm_v1';

abstract class SilverBackendGateway {
  Future<BackendRecognitionResult> recognizeDefault();

  Future<GuidanceOutputDto> createGuidance({
    required String templateId,
    required String userQueryText,
  });
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
  })  : _templates = templates ??
            TemplateRepositoryClient(baseUrl: defaultSilverTechApiBaseUrl),
        _guidance =
            guidance ?? GuidanceClient(baseUrl: defaultSilverTechApiBaseUrl),
        _visionLogs =
            visionLogs ?? VisionLogClient(baseUrl: defaultSilverTechApiBaseUrl);

  final TemplateRepositoryClient _templates;
  final GuidanceClient _guidance;
  final VisionLogClient _visionLogs;

  @override
  Future<BackendRecognitionResult> recognizeDefault() async {
    const double candidateConfidence = 0;
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
