import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:silvertech_mobile/templates/template_repository_client.dart';
import 'package:silvertech_mobile/vision/vision_match_client.dart';

void main() {
  test('posts multipart frame and parses accepted result', () async {
    late http.Request captured;
    final client = VisionMatchClient(
      baseUrl: 'http://api.test',
      httpClient: MockClient((http.Request request) async {
        captured = request;
        return http.Response(
          jsonEncode(<String, Object?>{
            'accepted': true,
            'template_id': 'template_panasonic_microwave_nn_gt35hm_v1',
            'match_score': 0.39,
            'failure_reason': null,
            'projected_buttons': <Object?>[
              <String, Object?>{
                'button_id': 'start',
                'polygon': <Object?>[
                  <String, Object?>{'x': 10.0, 'y': 20.0},
                  <String, Object?>{'x': 90.0, 'y': 20.0},
                  <String, Object?>{'x': 90.0, 'y': 70.0},
                  <String, Object?>{'x': 10.0, 'y': 70.0},
                ],
              },
            ],
          }),
          200,
        );
      }),
    );

    final result = await client.match(
      Uint8List.fromList('FAKEJPEG'.codeUnits),
      brand: 'Panasonic',
      applianceType: 'microwave',
    );

    expect(captured.method, 'POST');
    expect(captured.url.path, '/api/vision/match');
    expect(captured.headers['content-type'], contains('multipart/form-data'));
    expect(captured.body, contains('Panasonic'));
    expect(captured.body, contains('FAKEJPEG'));
    expect(result.accepted, isTrue);
    expect(result.templateId, 'template_panasonic_microwave_nn_gt35hm_v1');
    expect(result.matchScore, 0.39);
    expect(result.projectedButtons.single.buttonId, 'start');
    expect(result.projectedButtons.single.polygon.length, 4);
    expect(result.projectedButtons.single.polygon.first.x, 10.0);
  });

  test('throws FriendlyBackendException on 5xx', () async {
    final client = VisionMatchClient(
      baseUrl: 'http://api.test',
      httpClient: MockClient((http.Request request) async {
        return http.Response(
          jsonEncode(<String, Object?>{
            'detail': <String, Object?>{
              'message_vi': 'Loi may chu.',
              'recovery_action': 'rescan',
            },
          }),
          502,
        );
      }),
    );

    await expectLater(
      client.match(Uint8List.fromList('X'.codeUnits)),
      throwsA(isA<FriendlyBackendException>()
          .having((e) => e.statusCode, 'statusCode', 502)),
    );
  });
}
