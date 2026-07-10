import 'dart:typed_data';

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
  Future<BackendRecognitionResult> recognizeFromFrame(
      Uint8List frameBytes) {
    return recognizeDefault();
  }

  @override
  Future<TemplateDetailDto> fetchTemplate(String templateId) async {
    return (await recognizeDefault()).template;
  }

  @override
  Future<String> submitTemplate({
    required Uint8List imageBytes,
    required String brand,
    required String applianceType,
    required Map<String, Object?> Function(String imageUrl) buildLabels,
  }) async {
    return 'submission-fake';
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

class FakeDeviceLibraryStore implements DeviceLibraryStore {
  FakeDeviceLibraryStore([List<DemoDevice>? seedDevices])
      : _devices = List<DemoDevice>.from(seedDevices ?? const <DemoDevice>[]);

  List<DemoDevice> _devices;

  @override
  Future<List<DemoDevice>> loadDevices() async {
    return List<DemoDevice>.from(_devices);
  }

  @override
  Future<void> saveDevices(List<DemoDevice> devices) async {
    _devices = List<DemoDevice>.from(devices);
  }

  List<DemoDevice> get devices => List<DemoDevice>.from(_devices);
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
  Future<(FakeBackendGateway, FakeDeviceLibraryStore)> pumpApp(
    WidgetTester tester, {
    List<DemoDevice>? seedDevices,
  }) async {
    final fakeBackend = FakeBackendGateway();
    final fakeStore = FakeDeviceLibraryStore(
      seedDevices ??
          <DemoDevice>[
            const DemoDevice(
              id: 'tv',
              kind: 'tv',
              tone: 'blue',
              name: 'TV Samsung',
              short: 'UA55AU7000',
              model: 'UA55AU7000',
              last: 'Hôm nay, 14:30',
              templateId: 'template_panasonic_microwave_nn_gt35hm_v1',
            ),
            const DemoDevice(
              id: 'ac',
              kind: 'ac',
              tone: 'green',
              name: 'Điều hòa Daikin',
              short: 'FTKM35',
              model: 'FTKM35RVMV',
              last: 'Hôm qua',
              templateId: 'template_panasonic_microwave_nn_gt35hm_v1',
            ),
          ],
    );
    await tester.binding.setSurfaceSize(const Size(402, 874));
    await tester.pumpWidget(
      SilverTechApp(
        backend: fakeBackend,
        speechToText: FakeSpeechToTextClient(),
        deviceStore: fakeStore,
      ),
    );
    await tester.pumpAndSettle();
    return (fakeBackend, fakeStore);
  }

  testWidgets('runs home to voice to guidance prototype flow',
      (WidgetTester tester) async {
    final (fakeBackend, _) = await pumpApp(tester);

    expect(find.text('SILVERTECH'), findsOneWidget);
    expect(find.text('Xin chào!'), findsOneWidget);
    expect(find.text('Bắt đầu hướng dẫn'), findsOneWidget);
    expect(find.text('Đưa thiết bị vào khung'), findsOneWidget);

    await tester.tap(find.text('Bắt đầu hướng dẫn'));
    await tester.pumpAndSettle();

    expect(find.text('Nhận diện thiết bị'), findsOneWidget);
    expect(find.textContaining('Đang nhận diện trực tiếp'), findsOneWidget);
    expect(find.textContaining('94%'), findsWidgets);
    expect(find.text('độ tin cậy'), findsOneWidget);

    await tester.tap(find.text('Dùng kết quả này'));
    await tester.pumpAndSettle();

    expect(fakeBackend.recognitionCalls, 1);
    expect(fakeStore.devices.first.name, 'Lò vi sóng Panasonic');
    expect(fakeStore.devices.first.templateId,
      'template_panasonic_microwave_nn_gt35hm_v1');
    expect(find.textContaining('Lò vi sóng Panasonic'), findsOneWidget);
    expect(find.text('1 nút'), findsOneWidget);
    expect(find.text('Mic'), findsOneWidget);

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
    await tester.pumpAndSettle();

    expect(find.text('Nhận diện thiết bị'), findsOneWidget);
    expect(find.textContaining('Đang nhận diện trực tiếp'), findsOneWidget);
  });

  testWidgets('asks for guidance when voice is opened from a saved device card',
      (WidgetTester tester) async {
    // Tapping a device in "Đã dùng gần đây" skips the recognise screen, so the
    // shell has no template yet. Guidance must still work from there.
    final (fakeBackend, _) = await pumpApp(tester);

    await tester.tap(find.text('TV Samsung'));
    await tester.pumpAndSettle();

    expect(find.text('Mic'), findsOneWidget);

    await tester.tap(find.text('Mic'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Hỏi hướng dẫn'));
    await tester.pumpAndSettle();

    expect(find.text('Chưa nhận diện thiết bị. Quét lại.'), findsNothing);
    expect(fakeBackend.guidanceCalls, 1);
    expect(fakeBackend.lastTemplateId,
        'template_panasonic_microwave_nn_gt35hm_v1');
    expect(find.text('Nhấn nút Bắt đầu.'), findsOneWidget);
  });

  testWidgets('opens add-device wizard and requires a photo first',
      (WidgetTester tester) async {
    await pumpApp(tester);

    await tester.scrollUntilVisible(find.text('Thêm thiết bị mới'), 120);
    await tester.tap(find.text('Thêm thiết bị mới').first);
    await tester.pumpAndSettle();

    expect(find.text('Thêm thiết bị mới'), findsOneWidget);
    expect(find.text('Chụp ảnh mặt trước thiết bị'), findsOneWidget);
    expect(find.text('Chọn từ thư viện'), findsOneWidget);
    // No photo picked yet, so the wizard must not advance.
    await tester.tap(find.text('Tiếp theo'));
    await tester.pumpAndSettle();
    expect(find.text('Chụp ảnh mặt trước thiết bị'), findsOneWidget);
    expect(find.text('Thông tin thiết bị'), findsNothing);
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
