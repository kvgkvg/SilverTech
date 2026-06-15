import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:silvertech_mobile/backend/silver_backend.dart';
import 'package:silvertech_mobile/guidance/guidance_client.dart';
import 'package:silvertech_mobile/main.dart';
import 'package:silvertech_mobile/templates/template_repository_client.dart';
import 'package:silvertech_mobile/vision/vision_match_client.dart';
import 'package:silvertech_mobile/voice/stt_client.dart';

class FakeBackendGateway implements SilverBackendGateway {
  int recognitionCalls = 0;
  int matchCalls = 0;
  int guidanceCalls = 0;
  String? lastTemplateId;
  String? lastQuery;

  @override
  Future<VisionMatchResult> match(
    Uint8List frame, {
    String? brand,
    String? applianceType,
  }) async {
    matchCalls += 1;
    return const VisionMatchResult(
      accepted: true,
      templateId: 'template_panasonic_microwave_nn_gt35hm_v1',
      matchScore: 0.4,
    );
  }

  @override
  Future<TemplateDetailDto> fetchTemplate(String templateId) async {
    // Reuse the same TemplateDetailDto recognizeDefault returns.
    return (await recognizeDefault()).template;
  }

  @override
  Future<BackendRecognitionResult> recognizeDefault() async {
    recognitionCalls += 1;
    return const BackendRecognitionResult(
      template: TemplateDetailDto(
        id: 'template_panasonic_microwave_nn_gt35hm_v1',
        brand: 'Panasonic',
        applianceType: 'microwave',
        templateCode: 'panasonic_microwave_nn_gt35hm_v1',
        version: 1,
        status: 'official',
        templateImageUrl: 'data/templates/panasonic_microwave_nn_gt35hm.png',
        buttons: <TemplateButtonDto>[
          TemplateButtonDto(
            buttonId: 'start',
            label: 'Start',
            vietnameseName: 'Bắt đầu',
            functionDescription: 'Bắt đầu lò vi sóng',
            bbox: TemplateBBoxDto(x: 180, y: 235, width: 70, height: 55),
            buttonType: 'physical',
          ),
        ],
      ),
      matchScore: 0,
    );
  }

  @override
  Future<GuidanceOutputDto> createGuidance({
    required String templateId,
    required String userQueryText,
  }) async {
    guidanceCalls += 1;
    lastTemplateId = templateId;
    lastQuery = userQueryText;
    return const GuidanceOutputDto(
      intent: 'temperature_up',
      steps: <GuidanceStepDto>[
        GuidanceStepDto(
          stepNumber: 1,
          instructionVi: 'Nhấn nút Bắt đầu.',
          buttonId: 'start',
          expectedResult: 'Lò vi sóng bắt đầu chạy.',
        ),
      ],
    );
  }
}

class FakeSpeechToTextClient implements SpeechToTextClient {
  bool disposed = false;
  bool warmedUp = false;
  bool recording = false;

  @override
  bool get isRecording => recording;

  @override
  Future<void> warmUp() async {
    warmedUp = true;
  }

  @override
  Future<bool> startListening() async {
    recording = true;
    return true;
  }

  @override
  Future<String> stopAndTranscribe() async {
    recording = false;
    return 'Tăng nhiệt độ lên 27 độ';
  }

  @override
  Future<String> transcribeAsset(String assetKey) async {
    return 'Tăng nhiệt độ lên 27 độ';
  }

  @override
  void dispose() {
    disposed = true;
  }
}

void main() {
  Future<FakeBackendGateway> pumpApp(WidgetTester tester) async {
    final fakeBackend = FakeBackendGateway();
    await tester.binding.setSurfaceSize(const Size(402, 874));
    await tester.pumpWidget(
      SilverTechApp(
        backend: fakeBackend,
        speechToText: FakeSpeechToTextClient(),
      ),
    );
    await tester.pumpAndSettle();
    return fakeBackend;
  }

  testWidgets('runs home to voice to guidance prototype flow',
      (WidgetTester tester) async {
    final fakeBackend = await pumpApp(tester);

    expect(find.text('SILVERTECH'), findsOneWidget);
    expect(find.text('Xin chào!'), findsOneWidget);
    expect(find.text('Bắt đầu hướng dẫn'), findsOneWidget);
    expect(find.text('Đưa thiết bị vào khung'), findsOneWidget);

    await tester.tap(find.text('Bắt đầu hướng dẫn'));
    await tester.pump(); // enter recognition screen + start live loop

    expect(find.text('Nhận diện thiết bị'), findsOneWidget);
    expect(find.textContaining('Đang nhận diện trực tiếp'), findsOneWidget);
    expect(find.textContaining('0%'), findsWidgets);
    expect(find.text('độ tin cậy'), findsOneWidget);

    // The live loop opens a real FrameSource (camera->asset fallback) before it
    // arms its Timer.periodic(1s). Opening + the first asset load are real I/O,
    // so let the real event loop spin via runAsync until the source is ready.
    await tester.runAsync(() async {
      await Future<void>.delayed(const Duration(milliseconds: 300));
    });
    await tester.pump(); // flush the setState that armed the timer

    // Now the periodic timer lives in fake-async: pump intervals to advance the
    // detect ticks until the controller locks on (lockThreshold 2) and self-
    // stops. grabFrame returns the cached frame so each tick settles under pump.
    await tester.pump(const Duration(seconds: 1)); // tick 1 -> scanning
    await tester.pump();
    await tester.pump(const Duration(seconds: 1)); // tick 2 -> matched -> stop
    await tester.pumpAndSettle(); // fetchTemplate + matched UI; loop stopped

    expect(fakeBackend.matchCalls, greaterThan(0));
    expect(find.textContaining('Lò vi sóng Panasonic'), findsOneWidget);
    expect(find.text('1 nút'), findsOneWidget);

    await tester.tap(find.text('Dùng kết quả này'));
    await tester.pumpAndSettle();

    // Voice screen now carries the matched microwave template (button "Bắt đầu",
    // header "Panasonic • 1 nút từ DB"), not the old AC sample query.
    expect(find.text('Mic'), findsOneWidget);
    expect(find.textContaining('1 nút từ DB'), findsOneWidget);

    await tester.tap(find.text('Mic'));
    await tester.pumpAndSettle();

    expect(fakeBackend.guidanceCalls, 0);
    expect(fakeBackend.lastTemplateId, isNull);

    expect(find.textContaining('Tăng nhiệt độ lên 27 độ'), findsOneWidget);
    expect(find.text('Hỏi hướng dẫn'), findsOneWidget);

    await tester.tap(find.text('Hỏi hướng dẫn'));
    await tester.pumpAndSettle();

    expect(fakeBackend.guidanceCalls, 1);
    expect(fakeBackend.lastTemplateId,
        'template_panasonic_microwave_nn_gt35hm_v1');
    expect(find.text('Bước 1 / 1'), findsOneWidget);
    expect(find.text('Nhấn nút Bắt đầu.'), findsOneWidget);

    await tester.tap(find.text('Hoàn thành'));
    await tester.pumpAndSettle();

    expect(find.text('Mic'), findsOneWidget);
    expect(find.text('Sẵn sàng - giữ nút mic và nói câu hỏi'), findsOneWidget);
    expect(find.text('Xin chào!'), findsNothing);

    await tester.tap(find.byIcon(Icons.chevron_left).first);
    await tester.pump(); // back to recognize -> live loop restarts (do NOT settle)

    expect(find.text('Nhận diện thiết bị'), findsOneWidget);
    expect(find.textContaining('Đang nhận diện trực tiếp'), findsOneWidget);

    // Stop the restarted loop so no periodic Timer is pending at teardown.
    await tester.tap(find.byIcon(Icons.chevron_left).first);
    await tester.pumpAndSettle();
  });

  testWidgets('adds a device through four-step wizard',
      (WidgetTester tester) async {
    await pumpApp(tester);

    await tester.scrollUntilVisible(find.text('Thêm thiết bị mới'), 120);
    await tester.tap(find.text('Thêm thiết bị mới').first);
    await tester.pumpAndSettle();

    expect(find.text('Thêm thiết bị mới'), findsOneWidget);
    expect(find.text('Chụp ảnh'), findsOneWidget);
    expect(find.text('Chạm để chụp ảnh'), findsOneWidget);

    await tester.tap(find.text('Chạm để chụp ảnh'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Tiếp theo'));
    await tester.pumpAndSettle();

    expect(find.text('Hệ thống đang nhận diện'), findsOneWidget);
    await tester.tap(find.text('Tiếp theo'));
    await tester.pumpAndSettle();

    expect(find.text('Kiểm tra tên các nút'), findsOneWidget);
    await tester.tap(find.text('Tiếp theo'));
    await tester.pumpAndSettle();

    expect(find.text('Xác nhận và lưu'), findsOneWidget);
    await tester.tap(find.text('Lưu thiết bị'));
    await tester.pumpAndSettle();

    expect(find.text('Thiết bị của tôi'), findsOneWidget);
    expect(find.text('Điều hòa phòng khách'), findsOneWidget);
    expect(find.textContaining('Đã lưu'), findsOneWidget);
  });

  testWidgets('opens settings with accessibility controls',
      (WidgetTester tester) async {
    await pumpApp(tester);

    await tester.tap(find.text('Cài đặt'));
    await tester.pumpAndSettle();

    expect(find.text('Tuỳ chỉnh cho dễ dùng hơn'), findsOneWidget);
    expect(find.text('Cỡ chữ'), findsOneWidget);
    expect(find.text('Đọc to hướng dẫn'), findsOneWidget);
    expect(find.text('Độ tương phản cao'), findsOneWidget);
  });
}
