import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:silvertech_mobile/guidance/guidance_client.dart';
import 'package:silvertech_mobile/templates/template_repository_client.dart';

void main() {
  test('template client posts candidate context and parses templates',
      () async {
    late http.Request captured;
    final client = TemplateRepositoryClient(
      baseUrl: 'http://api.test',
      httpClient: MockClient((http.Request request) async {
        captured = request;
        return http.Response(
          jsonEncode(<String, Object?>{
            'candidates': <Object?>[
              <String, Object?>{
                'id': 'template_daikin_ac_remote_v1',
                'brand': 'Daikin',
                'appliance_type': 'air_conditioner',
                'template_code': 'daikin_ac_remote_v1',
                'version': 1,
                'status': 'official',
                'template_image_url': 'data/templates/daikin_ac_remote_v1.txt',
              },
            ],
          }),
          200,
        );
      }),
    );

    final candidates = await client.findCandidates(
      brand: 'Daikin',
      applianceType: 'air_conditioner',
      brandConfidence: 0.92,
    );

    expect(captured.method, 'POST');
    expect(captured.url.path, '/api/vision/candidates');
    expect(
      jsonDecode(captured.body),
      <String, Object?>{
        'brand': 'Daikin',
        'appliance_type': 'air_conditioner',
        'brand_confidence': 0.92,
      },
    );
    expect(candidates.single.id, 'template_daikin_ac_remote_v1');
    expect(candidates.single.applianceType, 'air_conditioner');
  });

  test('template client fetches detail and parses button definitions',
      () async {
    final client = TemplateRepositoryClient(
      baseUrl: 'http://api.test',
      httpClient: MockClient((http.Request request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/api/templates/template_daikin_ac_remote_v1');
        return http.Response(
          jsonEncode(<String, Object?>{
            'id': 'template_daikin_ac_remote_v1',
            'brand': 'Daikin',
            'appliance_type': 'air_conditioner',
            'template_code': 'daikin_ac_remote_v1',
            'version': 1,
            'status': 'official',
            'template_image_url': 'data/templates/daikin_ac_remote_v1.txt',
            'buttons': <Object?>[
              <String, Object?>{
                'button_id': 'temp_up',
                'label': 'Temp +',
                'vietnamese_name': 'Tang nhiet do',
                'function_description': 'Tang nhiet do dieu hoa',
                'bbox_template_coordinates': <String, Object?>{
                  'x': 180,
                  'y': 235,
                  'width': 70,
                  'height': 55,
                },
                'button_type': 'physical',
              },
            ],
          }),
          200,
        );
      }),
    );

    final detail = await client.fetchTemplate('template_daikin_ac_remote_v1');

    expect(detail.id, 'template_daikin_ac_remote_v1');
    expect(detail.buttons.single.buttonId, 'temp_up');
    expect(detail.buttons.single.vietnameseName, 'Tang nhiet do');
  });

  test('guidance client posts template query and parses validated steps',
      () async {
    late http.Request captured;
    final client = GuidanceClient(
      baseUrl: 'http://api.test',
      httpClient: MockClient((http.Request request) async {
        captured = request;
        return http.Response(
          jsonEncode(<String, Object?>{
            'intent': 'temperature_up',
            'steps': <Object?>[
              <String, Object?>{
                'step_number': 1,
                'instruction_vi': 'Nhan nut Tang nhiet do.',
                'button_id': 'temp_up',
                'expected_result': 'Nhiet do tang len.',
              },
            ],
            'safety_note': null,
          }),
          200,
        );
      }),
    );

    final guidance = await client.createGuidance(
      templateId: 'template_daikin_ac_remote_v1',
      userQueryText: 'Toi muon chinh nhiet do dieu hoa',
    );

    expect(captured.method, 'POST');
    expect(captured.url.path, '/api/query');
    expect(
      jsonDecode(captured.body),
      <String, Object?>{
        'template_id': 'template_daikin_ac_remote_v1',
        'user_query_text': 'Toi muon chinh nhiet do dieu hoa',
      },
    );
    expect(guidance.steps.single.buttonId, 'temp_up');
    expect(guidance.steps.single.instructionVi, 'Nhan nut Tang nhiet do.');
  });
}
