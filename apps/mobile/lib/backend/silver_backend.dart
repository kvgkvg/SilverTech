import '../guidance/guidance_client.dart';
import '../templates/template_repository_client.dart';

const String defaultSilverTechApiBaseUrl = String.fromEnvironment(
  'SILVERTECH_API_BASE_URL',
  defaultValue: 'http://10.0.2.2:8000',
);
const String defaultSilverTechMatchBrand = String.fromEnvironment(
  'SILVERTECH_MATCH_BRAND',
  defaultValue: 'Panasonic',
);
const String defaultSilverTechMatchApplianceType = String.fromEnvironment(
  'SILVERTECH_MATCH_APPLIANCE_TYPE',
  defaultValue: 'microwave',
);

abstract class SilverBackendGateway {
  Future<BackendRecognitionResult> recognizeDefault();

  Future<GuidanceOutputDto> createGuidance({
    required String templateId,
    required String userQueryText,
  });
}

class BackendRecognitionResult {
  const BackendRecognitionResult({required this.template});

  final TemplateDetailDto template;
}

class HttpSilverBackendGateway implements SilverBackendGateway {
  HttpSilverBackendGateway({
    TemplateRepositoryClient? templates,
    GuidanceClient? guidance,
  })  : _templates = templates ??
            TemplateRepositoryClient(baseUrl: defaultSilverTechApiBaseUrl),
        _guidance =
            guidance ?? GuidanceClient(baseUrl: defaultSilverTechApiBaseUrl);

  final TemplateRepositoryClient _templates;
  final GuidanceClient _guidance;

  @override
  Future<BackendRecognitionResult> recognizeDefault() async {
    final candidates = await _templates.findCandidates(
      brand: defaultSilverTechMatchBrand,
      applianceType: defaultSilverTechMatchApplianceType,
      brandConfidence: 0.92,
    );
    if (candidates.isEmpty) {
      throw const FriendlyBackendException(
        messageVi: 'Chưa tìm thấy mẫu thiết bị. Vui lòng chọn lại.',
        recoveryAction: 'manual_select',
        statusCode: 404,
      );
    }
    final template = await _templates.fetchTemplate(candidates.first.id);
    return BackendRecognitionResult(template: template);
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
