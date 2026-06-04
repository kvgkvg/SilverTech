import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:silvertech_mobile/backend/silver_backend.dart';
import 'package:silvertech_mobile/guidance/guidance_client.dart';
import 'package:silvertech_mobile/main.dart';
import 'package:silvertech_mobile/templates/template_repository_client.dart';
import 'package:silvertech_mobile/voice/stt_client.dart';

class FakeBackendGateway implements SilverBackendGateway {
  int recognitionCalls = 0;
  int guidanceCalls = 0;
  String? lastTemplateId;
  String? lastQuery;

  @override
  Future<BackendRecognitionResult> recognizeDefault() async {
    recognitionCalls += 1;
    return const BackendRecognitionResult(
      template: TemplateDetailDto(
        id: 'template_daikin_ac_remote_v1',
        brand: 'Daikin',
        applianceType: 'air_conditioner',
        templateCode: 'daikin_ac_remote_v1',
        version: 1,
        status: 'official',
        templateImageUrl: 'data/templates/daikin_ac_remote_v1.txt',
        buttons: <TemplateButtonDto>[
          TemplateButtonDto(
            buttonId: 'temp_up',
            label: 'Temp +',
            vietnameseName: 'Tăng nhiệt độ',
            functionDescription: 'Tăng nhiệt độ điều hòa',
            bbox: TemplateBBoxDto(x: 180, y: 235, width: 70, height: 55),
            buttonType: 'physical',
          ),
        ],
      ),
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
          instructionVi: 'Nhấn nút Tăng nhiệt độ.',
          buttonId: 'temp_up',
          expectedResult: 'Nhiệt độ tăng lên.',
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
    await tester.pumpAndSettle();

    expect(find.text('Nhận diện thiết bị'), findsOneWidget);
    expect(find.text('Đang nhận diện trực tiếp'), findsOneWidget);
    expect(find.text('6'), findsOneWidget);
    expect(find.text('nút bấm'), findsOneWidget);

    await tester.tap(find.text('Dùng kết quả này'));
    await tester.pumpAndSettle();

    expect(fakeBackend.recognitionCalls, 1);
    expect(find.textContaining('Điều hòa Daikin'), findsOneWidget);
    expect(find.text('1 nút'), findsOneWidget);
    expect(find.text('Mic'), findsOneWidget);
    expect(find.textContaining('Tăng nhiệt độ'), findsOneWidget);

    await tester.tap(find.text('Mic'));
    await tester.pumpAndSettle();

    expect(fakeBackend.guidanceCalls, 0);
    expect(fakeBackend.lastTemplateId, isNull);
    expect(find.text('Bước 1 / 3'), findsOneWidget);
    expect(find.text('Nút màu xanh phía bên phải điều khiển'), findsOneWidget);
    expect(find.text('Nhiệt độ +'), findsWidgets);

    await tester.tap(find.text('Tiếp theo'));
    await tester.pumpAndSettle();

    expect(find.text('Bước 2 / 3'), findsOneWidget);
    expect(find.text('Bấm thêm một lần nữa để lên 27°C'), findsOneWidget);

    await tester.tap(find.text('Tiếp theo'));
    await tester.pumpAndSettle();

    expect(find.text('Bước 3 / 3'), findsOneWidget);
    expect(find.text('Xong rồi!'), findsOneWidget);

    await tester.tap(find.text('Hoàn thành'));
    await tester.pumpAndSettle();

    expect(find.text('Mic'), findsOneWidget);
    expect(find.text('Sẵn sàng - giữ nút mic và nói câu hỏi'), findsOneWidget);
    expect(find.text('Xin chào!'), findsNothing);

    await tester.tap(find.byIcon(Icons.chevron_left).first);
    await tester.pumpAndSettle();

    expect(find.text('Nhận diện thiết bị'), findsOneWidget);
    expect(find.text('Đang nhận diện trực tiếp'), findsOneWidget);
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
