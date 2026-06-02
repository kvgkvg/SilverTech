class EventLogger {
  final List<Map<String, Object?>> events = <Map<String, Object?>>[];
  void log(String name, Map<String, Object?> payload) {
    events.add(<String, Object?>{'name': name, ...payload});
  }

  void logVision({
    required bool accepted,
    required String? templateId,
    required double matchScore,
    required String? failureReason,
  }) {
    log('vision_match', <String, Object?>{
      'accepted': accepted,
      'template_id': templateId,
      'match_score': matchScore,
      'failure_reason': failureReason,
    });
  }

  void logGuidance({
    required String templateId,
    required String query,
    required List<String> buttonIds,
  }) {
    log('llm_guidance', <String, Object?>{
      'template_id': templateId,
      'query': query,
      'button_ids': buttonIds,
    });
  }
}
