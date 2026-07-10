import 'dart:convert';
import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';

import 'backend/api_http_client.dart';
import 'backend/silver_backend.dart';
import 'guidance/guidance_client.dart';
import 'templates/template_repository_client.dart';
import 'vision/logo_anchor_client.dart';
import 'voice/stt_client.dart';
import 'voice/stt_factory.dart';
import 'voice/tts_manager.dart';

void main() {
  runApp(const SilverTechApp());
}

class SilverTechApp extends StatelessWidget {
  const SilverTechApp({
    this.backend,
    this.speechToText,
    this.deviceStore,
    super.key,
  });

  final SilverBackendGateway? backend;
  final SpeechToTextClient? speechToText;
  final DeviceLibraryStore? deviceStore;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SilverTech',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        scaffoldBackgroundColor: SilverTokens.bg,
        colorScheme: ColorScheme.fromSeed(seedColor: SilverTokens.blue),
        textTheme: const TextTheme(
          headlineLarge: TextStyle(fontSize: 30, fontWeight: FontWeight.w800),
          headlineMedium: TextStyle(fontSize: 24, fontWeight: FontWeight.w800),
          titleLarge: TextStyle(fontSize: 20, fontWeight: FontWeight.w800),
          bodyLarge: TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
          labelLarge: TextStyle(fontSize: 17, fontWeight: FontWeight.w800),
        ),
      ),
      home: SilverPrototypeShell(
        backend: backend ?? HttpSilverBackendGateway(),
        speechToText: speechToText,
        deviceStore: deviceStore,
      ),
    );
  }
}

class SilverTokens {
  static const Color bg = Color(0xFFF1F6FB);
  static const Color surface = Colors.white;
  static const Color surface2 = Color(0xFFF7FAFD);
  static const Color ink = Color(0xFF19293A);
  static const Color ink2 = Color(0xFF5C7184);
  static const Color ink3 = Color(0xFF93A6B7);
  static const Color blue = Color(0xFF2C77BE);
  static const Color blueDeep = Color(0xFF2462A6);
  static const Color blueBright = Color(0xFF3E8BD6);
  static const Color blueTint = Color(0xFFE4EFF8);
  static const Color blueTint2 = Color(0xFFD2E5F5);
  static const Color green = Color(0xFF1FA85A);
  static const Color greenBright = Color(0xFF2CC06C);
  static const Color greenTint = Color(0xFFE6F6EC);
  static const Color orange = Color(0xFFE47F27);
  static const Color orangeTint = Color(0xFFFBEEDF);
  static const Color red = Color(0xFFDB3B3B);
  static const Color redSoft = Color(0xFFF6E0E0);
  static const Color amberTint = Color(0xFFFCF3DA);
  static const Color amberLine = Color(0xFFE7B53E);
  static const Radius sheetRadius = Radius.circular(26);
}

class DemoDevice {
  const DemoDevice({
    required this.id,
    required this.kind,
    required this.tone,
    required this.name,
    required this.short,
    required this.model,
    required this.last,
    this.templateId,
  });

  final String id;
  final String kind;
  final String tone;
  final String name;
  final String short;
  final String model;
  final String last;
  final String? templateId;

  @override
  String toString() {
    return 'DemoDevice(id: $id, kind: $kind, tone: $tone, name: $name, '
        'short: $short, model: $model, last: $last, templateId: $templateId)';
  }

  DemoDevice copyWith({
    String? id,
    String? kind,
    String? tone,
    String? name,
    String? short,
    String? model,
    String? last,
    String? templateId,
  }) {
    return DemoDevice(
      id: id ?? this.id,
      kind: kind ?? this.kind,
      tone: tone ?? this.tone,
      name: name ?? this.name,
      short: short ?? this.short,
      model: model ?? this.model,
      last: last ?? this.last,
      templateId: templateId ?? this.templateId,
    );
  }

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'id': id,
      'kind': kind,
      'tone': tone,
      'name': name,
      'short': short,
      'model': model,
      'last': last,
      if (templateId != null) 'template_id': templateId,
    };
  }

  factory DemoDevice.fromJson(Map<String, Object?> json) {
    return DemoDevice(
      id: json['id'] as String,
      kind: json['kind'] as String,
      tone: json['tone'] as String,
      name: json['name'] as String,
      short: json['short'] as String,
      model: json['model'] as String,
      last: json['last'] as String,
      templateId: json['template_id'] as String?,
    );
  }
}

abstract class DeviceLibraryStore {
  Future<List<DemoDevice>> loadDevices();

  Future<void> saveDevices(List<DemoDevice> devices);
}

class JsonFileDeviceLibraryStore implements DeviceLibraryStore {
  JsonFileDeviceLibraryStore();

  static const String _storageKey = 'silvertech.device_library.v1';

  Future<File> _storageFile() async {
    final Directory directory = await getApplicationDocumentsDirectory();
    return File('${directory.path}/$_storageKey.json');
  }

  @override
  Future<List<DemoDevice>> loadDevices() async {
    final File file = await _storageFile();
    if (!await file.exists()) {
      return <DemoDevice>[];
    }
    try {
      final String raw = await file.readAsString();
      if (raw.isEmpty) {
        return <DemoDevice>[];
      }
      final List<dynamic> decoded = jsonDecode(raw) as List<dynamic>;
      return decoded
          .whereType<Map<String, dynamic>>()
          .map((Map<String, dynamic> json) => DemoDevice.fromJson(json))
          .toList();
    } catch (_) {
      return <DemoDevice>[];
    }
  }

  @override
  Future<void> saveDevices(List<DemoDevice> devices) async {
    final File file = await _storageFile();
    await file.writeAsString(
      jsonEncode(devices.map((DemoDevice device) => device.toJson()).toList()),
    );
  }
}

class GuideStepData {
  const GuideStepData({
    required this.kind,
    required this.buttonId,
    required this.title,
    required this.hint,
    this.audioUrl,
  });

  final String kind;
  final String buttonId;
  final String title;
  final String hint;
  final String? audioUrl;

  @override
  String toString() {
    return 'GuideStepData(kind: $kind, buttonId: $buttonId, title: $title, '
        'hint: $hint, audioUrl: $audioUrl)';
  }
}

class RouteState {
  const RouteState(this.screen, {this.device});

  final String screen;
  final DemoDevice? device;

  @override
  String toString() {
    return 'RouteState(screen: $screen, device: $device)';
  }
}

const DemoDevice acDevice = DemoDevice(
  id: 'ac',
  kind: 'ac',
  tone: 'green',
  name: 'Điều hòa Daikin',
  short: 'FTKM35',
  model: 'FTKM35RVMV',
  last: 'Hôm qua',
);

const List<DemoDevice> initialDevices = <DemoDevice>[
  DemoDevice(
    id: 'tv',
    kind: 'tv',
    tone: 'blue',
    name: 'TV Samsung',
    short: 'UA55AU7000',
    model: 'UA55AU7000',
    last: 'Hôm nay, 14:30',
  ),
  acDevice,
  DemoDevice(
    id: 'af',
    kind: 'fryer',
    tone: 'orange',
    name: 'Nồi chiên Philips',
    short: 'HD9252',
    model: 'HD9252/91',
    last: '3 ngày trước',
  ),
];

const List<GuideStepData> guideSteps = <GuideStepData>[
  GuideStepData(
    kind: 'Bấm nút',
    buttonId: 'tempup',
    title: 'Nhiệt độ +',
    hint: 'Nút màu xanh phía bên phải điều khiển',
  ),
  GuideStepData(
    kind: 'Bấm nút',
    buttonId: 'tempup',
    title: 'Nhiệt độ +',
    hint: 'Bấm thêm một lần nữa để lên 27°C',
  ),
  GuideStepData(
    kind: 'Kiểm tra',
    buttonId: 'mode',
    title: 'Xong rồi!',
    hint: 'Màn hình đã hiển thị 27°C - nhiệt độ đã tăng',
  ),
];

const TemplateDetailDto mockRecognizedTemplate = TemplateDetailDto(
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
    TemplateButtonDto(
      buttonId: 'temp_down',
      label: 'Temp -',
      vietnameseName: 'Giảm nhiệt độ',
      functionDescription: 'Giảm nhiệt độ điều hòa',
      bbox: TemplateBBoxDto(x: 75, y: 235, width: 70, height: 55),
      buttonType: 'physical',
    ),
    TemplateButtonDto(
      buttonId: 'power',
      label: 'Power',
      vietnameseName: 'Nguồn',
      functionDescription: 'Bật hoặc tắt điều hòa',
      bbox: TemplateBBoxDto(x: 220, y: 60, width: 55, height: 55),
      buttonType: 'physical',
    ),
    TemplateButtonDto(
      buttonId: 'mode',
      label: 'Mode',
      vietnameseName: 'Chế độ',
      functionDescription: 'Đổi chế độ hoạt động',
      bbox: TemplateBBoxDto(x: 75, y: 310, width: 70, height: 50),
      buttonType: 'physical',
    ),
    TemplateButtonDto(
      buttonId: 'fan',
      label: 'Fan',
      vietnameseName: 'Quạt',
      functionDescription: 'Đổi tốc độ quạt',
      bbox: TemplateBBoxDto(x: 180, y: 310, width: 70, height: 50),
      buttonType: 'physical',
    ),
    TemplateButtonDto(
      buttonId: 'timer',
      label: 'Timer',
      vietnameseName: 'Hẹn giờ',
      functionDescription: 'Cài hẹn giờ',
      bbox: TemplateBBoxDto(x: 130, y: 405, width: 75, height: 45),
      buttonType: 'physical',
    ),
  ],
);

class SilverPrototypeShell extends StatefulWidget {
  const SilverPrototypeShell({
    required this.backend,
    this.speechToText,
    this.deviceStore,
    super.key,
  });

  final SilverBackendGateway backend;
  final SpeechToTextClient? speechToText;
  final DeviceLibraryStore? deviceStore;

  @override
  State<SilverPrototypeShell> createState() => _SilverPrototypeShellState();
}

class _SilverPrototypeShellState extends State<SilverPrototypeShell> {
  List<DemoDevice> _devices = <DemoDevice>[];
  List<RouteState> _stack = const <RouteState>[RouteState('home')];
  String _tab = 'home';
  String? _toast;
  bool _recognitionBusy = false;
  bool _voiceBusy = false;
  double _recognitionMatchScore = 0.94;
  TemplateDetailDto? _selectedTemplate;

  /// Frame the user captured/uploaded for the last accepted recognition, plus
  /// the button quads the server projected onto it (frame pixel coordinates).
  /// Null/empty on the scripted demo path.
  Uint8List? _recognitionFrame;
  Map<String, List<ProjectedPoint>> _recognitionButtons =
      const <String, List<ProjectedPoint>>{};
  LogoFrameBox? _recognitionLogoBox;
  List<GuideStepData> _currentGuideSteps = guideSteps;
  late final SpeechToTextClient _stt;
  late final DeviceLibraryStore _deviceStore;
  Future<bool>? _startFuture;
  String _recognizedText = '';

  @override
  void initState() {
    super.initState();
    _stt = widget.speechToText ?? createPlatformSpeechToText();
    _deviceStore = widget.deviceStore ?? JsonFileDeviceLibraryStore();
    // Preload ASR model so first hold-to-talk is responsive.
    _stt.warmUp();
    unawaited(_restoreDevices());
  }

  @override
  void dispose() {
    _stt.dispose();
    super.dispose();
  }

  RouteState get _current => _stack.last;

  Future<void> _restoreDevices() async {
    final List<DemoDevice> savedDevices = await _deviceStore.loadDevices();
    if (!mounted) return;
    setState(() {
      _devices = savedDevices;
    });
  }

  List<DemoDevice> _upsertDeviceHistory(DemoDevice device) {
    return <DemoDevice>[
      device.copyWith(last: 'Vừa xong'),
      for (final DemoDevice existing in _devices)
        if (existing.id != device.id) existing,
    ];
  }

  Future<void> _persistDeviceHistory(DemoDevice device) async {
    final List<DemoDevice> updated = _upsertDeviceHistory(device);
    if (!mounted) return;
    setState(() {
      _devices = updated;
    });
    await _deviceStore.saveDevices(updated);
  }

  void _nav(String target, {DemoDevice? device}) {
    setState(() {
      _toast = null;
      if (target == 'back') {
        if (_stack.length > 1) {
          _stack = _stack.sublist(0, _stack.length - 1);
        }
        return;
      }
      if (target == 'home' || target == 'devices') {
        _tab = target;
        _stack = <RouteState>[RouteState(target)];
        return;
      }
      if (target == 'voice' && device != null) {
        unawaited(_persistDeviceHistory(device));
      }
      _stack = <RouteState>[..._stack, RouteState(target, device: device)];
    });
  }

  void _saveDevice(String name) {
    final DemoDevice newDevice = DemoDevice(
      id: DateTime.now().microsecondsSinceEpoch.toString(),
      kind: 'ac',
      tone: 'blue',
      name: name,
      short: 'Mới',
      model: 'Vừa thêm',
      last: 'Vừa xong',
    );
    unawaited(_persistDeviceHistory(newDevice));
    setState(() {
      _tab = 'devices';
      _stack = const <RouteState>[RouteState('devices')];
      _toast = 'Đã lưu "$name"';
    });
  }

  Future<void> _acceptBackendRecognition(Uint8List? frame) async {
    setState(() {
      _toast = null;
      _recognitionBusy = true;
    });
    try {
      // Real path: the captured frame goes to /api/vision/logo-anchor
      // (brand-first matching). No frame (camera unavailable, e.g. desktop
      // dev) keeps the scripted demo recognition.
      final result = frame != null
          ? await widget.backend.recognizeFromFrame(frame)
          : await widget.backend.recognizeDefault();
      final device = _deviceFromTemplate(result.template);
      if (!mounted) return;
      setState(() {
        _selectedTemplate = result.template;
        _recognitionMatchScore = result.matchScore;
        _recognitionFrame = result.projectedButtons.isEmpty ? null : frame;
        _recognitionButtons = result.projectedButtons;
        _recognitionLogoBox = result.logoFrameBox;
        _recognitionBusy = false;
        _stack = <RouteState>[..._stack, RouteState('voice', device: device)];
      });
      unawaited(_persistDeviceHistory(device));
    } on FriendlyBackendException catch (error) {
      if (!mounted) return;
      setState(() {
        _recognitionBusy = false;
        _toast = error.messageVi;
      });
    } on LogoAnchorException catch (error) {
      debugPrint('[RECOGNIZE] logo-anchor rejected: $error');
      if (!mounted) return;
      setState(() {
        _recognitionBusy = false;
        _toast = error.statusCode == 404
            ? 'Chưa nhận ra thiết bị trong ảnh. Thử ảnh rõ hơn.'
            : 'Không nhận diện được thiết bị. Vui lòng thử lại.';
      });
    } catch (error, stack) {
      debugPrint('[RECOGNIZE] failed: $error\n$stack');
      if (!mounted) return;
      setState(() {
        _recognitionBusy = false;
        _toast = 'Không nhận diện được thiết bị. Vui lòng thử lại.';
      });
    }
  }

  bool _sttBusy = false;

  Future<void> _startListening() async {
    setState(() => _recognizedText = '');
    final future = _stt.startListening();
    _startFuture = future;
    final ok = await future;
    if (!ok) {
      setState(() => _toast = 'Cần cấp quyền micro để nói câu hỏi.');
    }
  }

  /// Stops mic, runs on-device ASR, shows the recognized text in the UI.
  /// Does NOT auto-navigate — user reads the transcript then asks for guidance.
  Future<void> _stopAndTranscribe(DemoDevice device) async {
    // Ensure capture actually started before stopping (avoids stop-before-start
    // race on fast taps / first-use permission prompt → empty waveform).
    await _startFuture;
    _startFuture = null;
    setState(() => _sttBusy = true);
    String query;
    try {
      query = await _stt.stopAndTranscribe();
    } catch (e, st) {
      debugPrint('[STT] transcribe error: $e\n$st');
      setState(() {
        _sttBusy = false;
        _recognizedText = '';
        _toast = 'Không nhận diện được giọng nói. Thử lại.';
      });
      return;
    }
    debugPrint('[STT] recognized: "$query"');
    setState(() {
      _sttBusy = false;
      _recognizedText = query;
      _toast =
          query.isEmpty ? 'Chưa nghe rõ câu hỏi. Giữ nút và nói lại.' : null;
    });
  }

  /// Loads the demo template when the voice screen was reached without going
  /// through recognition — tapping a saved device card skips that screen.
  Future<TemplateDetailDto?> _ensureTemplate() async {
    if (_selectedTemplate != null) {
      return _selectedTemplate;
    }
    final DemoDevice? device = _current.device;
    final String? templateId = device?.templateId;
    if (templateId == null) {
      return null;
    }
    try {
      final TemplateDetailDto template =
          await widget.backend.fetchTemplate(templateId);
      if (!mounted) return null;
      setState(() {
        _selectedTemplate = template;
      });
      return template;
    } catch (_) {
      return null;
    }
  }

  Future<void> _askBackendGuidance(DemoDevice device,
      {required String query}) async {
    final TemplateDetailDto? template = await _ensureTemplate();
    if (!mounted) return;
    final String? templateId = template?.id;
    if (templateId == null) {
      setState(() => _toast = 'Chưa nhận diện thiết bị. Quét lại.');
      return;
    }
    setState(() {
      _voiceBusy = true;
      _toast = null;
    });
    try {
      final GuidanceOutputDto guidance = await widget.backend.createGuidance(
        templateId: templateId,
        userQueryText: query,
      );
      debugPrint('[GUIDE] intent=${guidance.intent} '
          'steps=${guidance.steps.length}');
      if (guidance.steps.isEmpty) {
        // Out-of-scope refusal: no button steps, just tell the user.
        setState(() {
          _voiceBusy = false;
          _toast = guidance.safetyNote ??
              'Câu hỏi không liên quan đến thiết bị này. '
                  'Hãy hỏi về cách sử dụng thiết bị.';
        });
        return;
      }
      setState(() {
        _currentGuideSteps = _mapGuidanceSteps(guidance);
        _voiceBusy = false;
        _toast = null;
        _stack = <RouteState>[..._stack, RouteState('guide', device: device)];
      });
    } on FriendlyBackendException catch (e) {
      debugPrint('[GUIDE] backend error ${e.statusCode}: ${e.messageVi}');
      setState(() {
        _voiceBusy = false;
        _toast = e.messageVi;
      });
    } catch (e) {
      debugPrint('[GUIDE] error: $e');
      setState(() {
        _voiceBusy = false;
        _toast = 'Không lấy được hướng dẫn. Thử lại.';
      });
    }
  }

  List<GuideStepData> _mapGuidanceSteps(GuidanceOutputDto guidance) {
    final List<GuideStepData> steps = <GuideStepData>[
      for (final GuidanceStepDto s in guidance.steps)
        GuideStepData(
          kind: 'Bấm nút',
          buttonId: s.buttonId,
          title: s.instructionVi,
          hint: s.expectedResult,
          audioUrl: s.audioUrl,
        ),
    ];
    final String? note = guidance.safetyNote;
    if (note != null && note.isNotEmpty) {
      steps.add(GuideStepData(
        kind: 'Lưu ý',
        buttonId: steps.isNotEmpty ? steps.last.buttonId : '',
        title: 'Lưu ý an toàn',
        hint: note,
      ));
    }
    return steps;
  }

  DemoDevice _deviceFromTemplate(TemplateDetailDto template) {
    final isAc = template.applianceType == 'air_conditioner';
    final isMicrowave = template.applianceType == 'microwave';
    return DemoDevice(
      id: template.id,
      kind: isAc
          ? 'ac'
          : isMicrowave
              ? 'microwave'
              : 'tv',
      tone: isAc
          ? 'green'
          : isMicrowave
              ? 'orange'
              : 'blue',
      name: isAc
          ? 'Điều hòa ${template.brand}'
          : isMicrowave
              ? 'Lò vi sóng ${template.brand}'
              : '${template.brand} ${template.applianceType}',
      short: template.templateCode,
      model: template.templateCode,
      last: 'Vừa nhận diện',
      templateId: template.id,
    );
  }

  @override
  Widget build(BuildContext context) {
    final bool dark = _current.screen == 'voice' || _current.screen == 'guide';
    final Widget content = switch (_current.screen) {
      'home' => HomeScreen(
          devices: _devices,
          onNavigate: _nav,
        ),
      'devices' => DevicesScreen(
          devices: _devices,
          onNavigate: _nav,
        ),
      'recognize' => RecognizeScreen(
          onNavigate: _nav,
          onUseResult: _acceptBackendRecognition,
          busy: _recognitionBusy,
          matchScore: _recognitionMatchScore,
        ),
      'voice' => VoiceScreen(
          device: _current.device ?? acDevice,
          template: _selectedTemplate,
          recognitionFrame: _recognitionFrame,
          projectedButtons: _recognitionButtons,
          logoFrameBox: _recognitionLogoBox,
          buttonCount: _selectedTemplate?.buttons.length ?? 6,
          busy: _voiceBusy,
          sttBusy: _sttBusy,
          recognizedText: _recognizedText,
          onNavigate: _nav,
          onStartListening: _startListening,
          onStopListening: _stopAndTranscribe,
          onAskGuidance: (device) =>
              _askBackendGuidance(device, query: _recognizedText),
        ),
      'guide' => GuideScreen(
          device: _current.device ?? acDevice,
          template: _selectedTemplate,
          recognitionFrame: _recognitionFrame,
          projectedButtons: _recognitionButtons,
          logoFrameBox: _recognitionLogoBox,
          steps: _currentGuideSteps,
          onNavigate: _nav,
        ),
      'add' => AddDeviceScreen(
          backend: widget.backend,
          onNavigate: _nav,
          onSave: _saveDevice,
        ),
      'settings' => SettingsScreen(onNavigate: _nav),
      _ => HomeScreen(
          devices: _devices,
          onNavigate: _nav,
        ),
    };

    if (_current.screen == 'home' || _current.screen == 'devices') {
      return Scaffold(
        backgroundColor: SilverTokens.bg,
        body: SafeArea(bottom: false, child: content),
        bottomNavigationBar: PrototypeTabBar(
          active: _tab,
          onHome: () => _nav('home'),
          onDevices: () => _nav('devices'),
        ),
        floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
        floatingActionButton:
            _toast == null ? null : ToastBanner(text: _toast!),
      );
    }

    return Scaffold(
      backgroundColor: dark ? const Color(0xFF0E141B) : SilverTokens.bg,
      body: SafeArea(bottom: false, child: content),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
      floatingActionButton: _toast == null ? null : ToastBanner(text: _toast!),
    );
  }
}

class HomeScreen extends StatelessWidget {
  const HomeScreen({
    required this.devices,
    required this.onNavigate,
    super.key,
  });

  final List<DemoDevice> devices;
  final void Function(String target, {DemoDevice? device}) onNavigate;

  @override
  Widget build(BuildContext context) {
    final List<String> steps = <String>[
      'Đưa thiết bị vào khung',
      'Hỏi bằng giọng nói',
      'Làm theo nút sáng',
    ];
    final List<Widget> recentCards = devices.isEmpty
        ? <Widget>[
            const _EmptyDeviceState(
              title: 'Chưa có thiết bị nào',
              subtitle: 'Thiết bị sẽ xuất hiện sau lần đầu bạn dùng hoặc lưu.',
            ),
          ]
        : devices
            .take(2)
            .map(
              (DemoDevice device) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: DeviceRow(
                  device: device,
                  onTap: () => onNavigate('voice', device: device),
                ),
              ),
            )
            .toList();
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 18),
      children: <Widget>[
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'SILVERTECH',
                    style: TextStyle(
                      color: SilverTokens.blue,
                      fontSize: 13,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 2.4,
                    ),
                  ),
                  SizedBox(height: 2),
                  Text(
                    'Xin chào!',
                    style: TextStyle(
                      color: SilverTokens.ink,
                      fontSize: 30,
                      height: 1.08,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  SizedBox(height: 6),
                  Text(
                    'Hôm nay ông/bà cần giúp gì?',
                    style: TextStyle(
                      color: SilverTokens.ink2,
                      fontSize: 17,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            ),
            SettingsButton(onTap: () => onNavigate('settings')),
          ],
        ),
        const SizedBox(height: 22),
        BigStartButton(onTap: () => onNavigate('recognize')),
        const SizedBox(height: 14),
        HowToHintCard(steps: steps),
        const SizedBox(height: 17),
        const Text(
          'Đã dùng gần đây',
          style: TextStyle(
            color: SilverTokens.ink,
            fontSize: 19,
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: 12),
        ...recentCards,
        SecondaryDashedButton(
          label: 'Thêm thiết bị mới',
          icon: Icons.add,
          onTap: () => onNavigate('add'),
        ),
      ],
    );
  }
}

class RecognizeScreen extends StatefulWidget {
  const RecognizeScreen({
    required this.onNavigate,
    required this.onUseResult,
    required this.busy,
    required this.matchScore,
    super.key,
  });

  final void Function(String target, {DemoDevice? device}) onNavigate;
  final Future<void> Function(Uint8List? frame) onUseResult;
  final bool busy;
  final double matchScore;

  @override
  State<RecognizeScreen> createState() => _RecognizeScreenState();
}

class _RecognizeScreenState extends State<RecognizeScreen> {
  final GlobalKey<_CameraCardState> _cameraKey = GlobalKey<_CameraCardState>();

  void Function(String target, {DemoDevice? device}) get onNavigate =>
      widget.onNavigate;
  bool get busy => widget.busy;
  double get matchScore => widget.matchScore;

  Future<void> _captureAndUse() async {
    final Uint8List? frame = await _cameraKey.currentState?.captureFrame();
    await widget.onUseResult(frame);
  }

  /// Alternative to the live camera: pick a photo of the appliance panel
  /// from the device gallery / file system and run recognition on it.
  Future<void> _pickAndUse() async {
    final XFile? file =
        await ImagePicker().pickImage(source: ImageSource.gallery);
    if (file == null) return;
    final Uint8List bytes = await file.readAsBytes();
    await widget.onUseResult(bytes);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: <Widget>[
        AppHeader(
            title: 'Nhận diện thiết bị', onBack: () => onNavigate('back')),
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 10),
            children: <Widget>[
              CameraCard(key: _cameraKey, scanning: true),
              const SizedBox(height: 16),
              Center(
                child: StatusPill(
                  label:
                      'Đang nhận diện trực tiếp • ${(matchScore * 100).round()}%',
                  color: SilverTokens.green,
                  bg: SilverTokens.greenTint,
                ),
              ),
              const SizedBox(height: 14),
              const Text(
                'Camera tự tìm thiết bị và nút bấm',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: SilverTokens.ink,
                  fontSize: 21,
                  height: 1.16,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 6),
              const Text(
                'Giữ điện thoại ổn định để hệ thống khoanh vùng các nút',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: SilverTokens.ink2,
                  fontSize: 16,
                  height: 1.35,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: <Widget>[
                  const Expanded(
                      child:
                          StatBox(big: '1', small: 'thiết bị', tone: 'green')),
                  const SizedBox(width: 12),
                  Expanded(
                    child: StatBox(
                      big: '${(matchScore * 100).round()}%',
                      small: 'độ tin cậy',
                      tone: 'green',
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              NeutralButton(
                label: busy ? 'Đang nhận diện...' : 'Tải ảnh thiết bị lên',
                icon: Icons.photo_library,
                enabled: !busy,
                onTap: _pickAndUse,
              ),
            ],
          ),
        ),
        FooterActions(
          children: <Widget>[
            Expanded(
              flex: 4,
              child: NeutralButton(
                label: 'Thử lại',
                icon: Icons.refresh,
                onTap: () => onNavigate('back'),
              ),
            ),
            const SizedBox(width: 11),
            Expanded(
              flex: 6,
              child: GreenButton(
                label: busy ? 'Đang nhận diện...' : 'Dùng kết quả này',
                icon: Icons.check,
                enabled: !busy,
                onTap: _captureAndUse,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class VoiceScreen extends StatefulWidget {
  const VoiceScreen({
    required this.device,
    required this.template,
    this.recognitionFrame,
    this.projectedButtons = const <String, List<ProjectedPoint>>{},
    this.logoFrameBox,
    required this.buttonCount,
    required this.busy,
    required this.sttBusy,
    required this.recognizedText,
    required this.onNavigate,
    required this.onStartListening,
    required this.onStopListening,
    required this.onAskGuidance,
    super.key,
  });

  final DemoDevice device;
  final TemplateDetailDto? template;
  final Uint8List? recognitionFrame;
  final Map<String, List<ProjectedPoint>> projectedButtons;
  final LogoFrameBox? logoFrameBox;
  final int buttonCount;
  final bool busy;
  final bool sttBusy;
  final String recognizedText;
  final void Function(String target, {DemoDevice? device}) onNavigate;
  final Future<void> Function() onStartListening;
  final Future<void> Function(DemoDevice device) onStopListening;
  final Future<void> Function(DemoDevice device) onAskGuidance;

  @override
  State<VoiceScreen> createState() => _VoiceScreenState();
}

class _VoiceScreenState extends State<VoiceScreen> {
  bool holding = false;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: <Widget>[
        DarkDeviceHeader(
          device: widget.device,
          trailing: StatusPill(
            label: '${widget.buttonCount} nút',
            color: Colors.white,
            bg: const Color(0x22FFFFFF),
            dot: false,
          ),
          onBack: () => widget.onNavigate('back'),
        ),
        Expanded(
          child: LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              return SingleChildScrollView(
                child: ConstrainedBox(
                  constraints: BoxConstraints(minHeight: constraints.maxHeight),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: <Widget>[
                      Padding(
                        padding: const EdgeInsets.fromLTRB(16, 6, 16, 0),
                        child: widget.template == null
                            ? const RemotePanel(display: '26°C', height: 300)
                            : widget.recognitionFrame != null &&
                                    widget.projectedButtons.isNotEmpty
                                // Real recognition: show the user's own photo
                                // with the projected button quads.
                                ? FrameOverlayPanel(
                                    frameBytes: widget.recognitionFrame!,
                                    projectedButtons: widget.projectedButtons,
                                    logoFrameBox: widget.logoFrameBox,
                                    template: widget.template!,
                                  )
                                : TemplateDataPanel(
                                    template: widget.template!,
                                  ),
                      ),
                      Padding(
                        padding: const EdgeInsets.fromLTRB(20, 20, 20, 48),
                        child: Column(
                          children: <Widget>[
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 18, vertical: 11),
                              decoration: BoxDecoration(
                                color: Colors.white.withValues(alpha: 0.08),
                                borderRadius: BorderRadius.circular(14),
                              ),
                              child: Text(
                                holding
                                    ? 'Đang nghe... hãy nói câu hỏi của ông/bà'
                                    : widget.sttBusy
                                        ? 'Đang nhận diện giọng nói...'
                                        : widget.busy
                                            ? 'Đang hỏi backend...'
                                            : 'Sẵn sàng - giữ nút mic và nói câu hỏi',
                                textAlign: TextAlign.center,
                                style: const TextStyle(
                                  color: Color(0xFFE9EEF4),
                                  fontSize: 15,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                            if (widget.recognizedText.isNotEmpty) ...<Widget>[
                              const SizedBox(height: 14),
                              _TranscriptCard(text: widget.recognizedText),
                              const SizedBox(height: 14),
                              SizedBox(
                                width: double.infinity,
                                child: PrimaryButton(
                                  label: 'Hỏi hướng dẫn',
                                  icon: Icons.help_outline,
                                  enabled: !widget.busy,
                                  onTap: () =>
                                      widget.onAskGuidance(widget.device),
                                ),
                              ),
                            ],
                            const SizedBox(height: 22),
                            GestureDetector(
                              onTapDown: (_) {
                                if (widget.busy || widget.sttBusy) return;
                                setState(() => holding = true);
                                widget.onStartListening();
                              },
                              onTapUp: (_) {
                                if (!holding) return;
                                setState(() => holding = false);
                                widget.onStopListening(widget.device);
                              },
                              onTapCancel: () =>
                                  setState(() => holding = false),
                              child: AnimatedScale(
                                scale: holding ? 1.06 : 1,
                                duration: const Duration(milliseconds: 150),
                                child: Container(
                                  width: 92,
                                  height: 92,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    gradient: const LinearGradient(
                                      colors: <Color>[
                                        SilverTokens.blueBright,
                                        SilverTokens.blueDeep
                                      ],
                                      begin: Alignment.topLeft,
                                      end: Alignment.bottomRight,
                                    ),
                                    boxShadow: <BoxShadow>[
                                      BoxShadow(
                                        color: SilverTokens.blueDeep
                                            .withValues(alpha: 0.45),
                                        blurRadius: 30,
                                        offset: const Offset(0, 14),
                                      ),
                                    ],
                                  ),
                                  child: const Column(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: <Widget>[
                                      Icon(Icons.mic,
                                          color: Colors.white, size: 34),
                                      Text(
                                        'Mic',
                                        style: TextStyle(
                                          color: Colors.white,
                                          fontSize: 13,
                                          fontWeight: FontWeight.w900,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                            const SizedBox(height: 16),
                            const Text(
                              'Bấm giữ và hỏi',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                color: Color(0xB3FFFFFF),
                                fontSize: 15,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}

class GuideScreen extends StatefulWidget {
  const GuideScreen({
    required this.device,
    required this.template,
    this.recognitionFrame,
    this.projectedButtons = const <String, List<ProjectedPoint>>{},
    this.logoFrameBox,
    required this.steps,
    required this.onNavigate,
    super.key,
  });

  final DemoDevice device;
  final TemplateDetailDto? template;
  final Uint8List? recognitionFrame;
  final Map<String, List<ProjectedPoint>> projectedButtons;
  final LogoFrameBox? logoFrameBox;
  final List<GuideStepData> steps;
  final void Function(String target, {DemoDevice? device}) onNavigate;

  @override
  State<GuideScreen> createState() => _GuideScreenState();
}

class _GuideScreenState extends State<GuideScreen> {
  int step = 0;
  final TtsManager _tts = TtsManager();

  @override
  void initState() {
    super.initState();
    // Read the first step aloud as soon as guidance opens.
    WidgetsBinding.instance.addPostFrameCallback((_) => _speakCurrent());
  }

  @override
  void dispose() {
    _tts.dispose();
    super.dispose();
  }

  /// Audio is best-effort: a step without `audio_url`, an unreachable backend,
  /// or a browser blocking autoplay must never break the guidance flow.
  void _speakCurrent() {
    unawaited(_tts.speak(widget.steps[step].audioUrl).catchError((_) {}));
  }

  /// Jump to [next] step (clamped) and read it aloud.
  void _go(int next) {
    final int clamped = next.clamp(0, widget.steps.length - 1);
    setState(() => step = clamped);
    _speakCurrent();
  }

  @override
  Widget build(BuildContext context) {
    final GuideStepData current = widget.steps[step];
    final bool done = step == widget.steps.length - 1;
    return Column(
      children: <Widget>[
        DarkDeviceHeader(
          device: widget.device,
          trailing: IconButton(
            icon: const Icon(Icons.volume_up, color: Colors.white),
            tooltip: 'Đọc lại bước này',
            onPressed: _speakCurrent,
          ),
          onBack: () => widget.onNavigate('back'),
        ),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 6, 16, 10),
            child: widget.template == null
                ? RemotePanel(
                    display: done ? '27°C' : '26°C',
                    highlight: done ? null : current.buttonId,
                    showArrow: !done,
                    height: 300,
                  )
                : widget.recognitionFrame != null &&
                        widget.projectedButtons.isNotEmpty
                    // Real recognition: highlight the current step's button
                    // directly on the user's photo.
                    ? FrameOverlayPanel(
                        frameBytes: widget.recognitionFrame!,
                        projectedButtons: widget.projectedButtons,
                        logoFrameBox: widget.logoFrameBox,
                        template: widget.template!,
                        activeButtonId: current.buttonId,
                      )
                    : TemplateDataPanel(
                        template: widget.template!,
                        activeButtonId: current.buttonId,
                      ),
          ),
        ),
        Container(
          padding: const EdgeInsets.fromLTRB(20, 18, 20, 30),
          decoration: const BoxDecoration(
            color: SilverTokens.bg,
            borderRadius: BorderRadius.only(
              topLeft: SilverTokens.sheetRadius,
              topRight: SilverTokens.sheetRadius,
            ),
            boxShadow: <BoxShadow>[
              BoxShadow(
                  color: Color(0x66000000),
                  blurRadius: 30,
                  offset: Offset(0, -8)),
            ],
          ),
          child: Column(
            children: <Widget>[
              Row(
                children: <Widget>[
                  Expanded(
                    child: Row(
                      children: widget.steps.indexed
                          .map(
                            (entry) => AnimatedContainer(
                              duration: const Duration(milliseconds: 200),
                              width: entry.$1 == step ? 22 : 8,
                              height: 8,
                              margin: const EdgeInsets.only(right: 7),
                              decoration: BoxDecoration(
                                color: entry.$1 == step
                                    ? SilverTokens.blue
                                    : entry.$1 < step
                                        ? SilverTokens.blueTint2
                                        : const Color(0xFFD7E2EC),
                                borderRadius: BorderRadius.circular(4),
                              ),
                            ),
                          )
                          .toList(),
                    ),
                  ),
                  Text(
                    'Bước ${step + 1} / ${widget.steps.length}',
                    style: const TextStyle(
                      color: SilverTokens.ink2,
                      fontSize: 15,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              InstructionCard(step: step, data: current, done: done),
              const SizedBox(height: 14),
              if (!done)
                Row(
                  children: <Widget>[
                    Expanded(
                        child: NeutralButton(
                            label: 'Lặp lại',
                            icon: Icons.refresh,
                            compact: true,
                            onTap: _speakCurrent)),
                    const SizedBox(width: 8),
                    Expanded(
                      child: NeutralButton(
                        label: 'Trước',
                        icon: Icons.arrow_back,
                        compact: true,
                        enabled: step > 0,
                        onTap: () => _go(step - 1),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: PrimaryButton(
                        label: 'Tiếp theo',
                        iconAfter: Icons.arrow_forward,
                        compact: true,
                        onTap: () => _go(step + 1),
                      ),
                    ),
                  ],
                )
              else
                Row(
                  children: <Widget>[
                    Expanded(
                        child: NeutralButton(
                            label: 'Làm lại',
                            icon: Icons.refresh,
                            onTap: () => _go(0))),
                    const SizedBox(width: 10),
                    Expanded(
                      flex: 2,
                      child: GreenButton(
                          label: 'Hoàn thành',
                          icon: Icons.check,
                          onTap: () => widget.onNavigate('back')),
                    ),
                  ],
                ),
            ],
          ),
        ),
      ],
    );
  }
}

/// One labeled button box drawn by the user (rect in image pixel coords).
class LabeledButtonBox {
  LabeledButtonBox({required this.rect, required this.name, this.usage = ''});

  Rect rect;
  String name;

  /// What the button does (function_description); falls back to [name].
  String usage;
}

/// Appliance type choices; value = backend appliance_type, label = Vietnamese.
const List<(String, String)> kApplianceTypes = <(String, String)>[
  ('washer', 'Máy giặt'),
  ('microwave', 'Lò vi sóng'),
  ('air_conditioner', 'Điều hòa'),
  ('tv', 'TV'),
  ('other', 'Khác'),
];

class AddDeviceScreen extends StatefulWidget {
  const AddDeviceScreen({
    required this.backend,
    required this.onNavigate,
    required this.onSave,
    super.key,
  });

  final SilverBackendGateway backend;
  final void Function(String target, {DemoDevice? device}) onNavigate;
  final void Function(String name) onSave;

  @override
  State<AddDeviceScreen> createState() => _AddDeviceScreenState();
}

class _AddDeviceScreenState extends State<AddDeviceScreen> {
  int step = 0;
  bool submitting = false;

  // Step 0 - photo.
  Uint8List? photo;
  Size? photoSize;

  // Step 1 - the only fields the user has to type; everything else is
  // derived (ids, template_code, display name, panel bbox, button ids).
  final TextEditingController brandController = TextEditingController();
  final TextEditingController modelController = TextEditingController();
  final TextEditingController customTypeController = TextEditingController();
  String applianceType = 'washer';

  // Step 2 - labeling: first drawn box is the brand logo, the rest are
  // buttons.
  Rect? logoBox;
  List<LabeledButtonBox> buttons = <LabeledButtonBox>[];

  @override
  void dispose() {
    brandController.dispose();
    modelController.dispose();
    customTypeController.dispose();
    super.dispose();
  }

  // ---- auto-assigned fields -------------------------------------------

  String _slug(String value) {
    final String lowered = value.trim().toLowerCase();
    final String replaced = lowered.replaceAll(RegExp(r'[^a-z0-9]+'), '_');
    return replaced.replaceAll(RegExp(r'^_+|_+$'), '');
  }

  /// "Khác" lets the user type their own appliance type; the slug of that
  /// text becomes the backend appliance_type.
  String get effectiveApplianceType {
    if (applianceType != 'other') return applianceType;
    final String custom = _slug(customTypeController.text);
    return custom.isEmpty ? 'other' : custom;
  }

  String get _baseSlug {
    final List<String> parts = <String>[
      _slug(brandController.text),
      _slug(effectiveApplianceType),
      if (_slug(modelController.text).isNotEmpty) _slug(modelController.text),
    ];
    return parts.where((String p) => p.isNotEmpty).join('_');
  }

  String get autoDeviceId =>
      'device_${_slug(brandController.text)}_${_slug(effectiveApplianceType)}_01';
  String get autoTemplateId => 'template_$_baseSlug';
  String get autoTemplateCode => '${_baseSlug}_v1';

  String get autoDisplayName {
    final String typeVi = applianceType == 'other'
        ? (customTypeController.text.trim().isEmpty
            ? 'Thiết bị'
            : customTypeController.text.trim())
        : kApplianceTypes
            .firstWhere((t) => t.$1 == applianceType,
                orElse: () => ('other', 'Thiết bị'))
            .$2;
    final String brand = brandController.text.trim();
    final String model = modelController.text.trim();
    return <String>[typeVi, brand, model]
        .where((String p) => p.isNotEmpty)
        .join(' ');
  }

  /// Panel bbox auto-assigned: union of logo + button boxes + 5% margin.
  Rect? get autoPanelBox {
    final List<Rect> rects = <Rect>[
      if (logoBox != null) logoBox!,
      ...buttons.map((b) => b.rect),
    ];
    if (rects.isEmpty || photoSize == null) return null;
    Rect union = rects.first;
    for (final Rect r in rects.skip(1)) {
      union = union.expandToInclude(r);
    }
    final double mx = union.width * 0.05;
    final double my = union.height * 0.05;
    return Rect.fromLTRB(
      (union.left - mx).clamp(0.0, photoSize!.width),
      (union.top - my).clamp(0.0, photoSize!.height),
      (union.right + mx).clamp(0.0, photoSize!.width),
      (union.bottom + my).clamp(0.0, photoSize!.height),
    );
  }

  Map<String, Object?> _bboxJson(Rect r) => <String, Object?>{
        'x': r.left.round(),
        'y': r.top.round(),
        'width': r.width.round(),
        'height': r.height.round(),
      };

  Map<String, Object?> _buildLabels(String imageUrl) {
    final String now = DateTime.now().toUtc().toIso8601String();
    return <String, Object?>{
      'device': <String, Object?>{
        'id': autoDeviceId,
        'brand': brandController.text.trim(),
        'appliance_type': effectiveApplianceType,
        'model_name': modelController.text.trim(),
        'display_name': autoDisplayName,
        'status': 'submitted',
        'created_at': now,
        'updated_at': now,
      },
      'template': <String, Object?>{
        'id': autoTemplateId,
        'device_id': autoDeviceId,
        'template_code': autoTemplateCode,
        'template_image_url': imageUrl,
        'logo_bbox': logoBox == null ? null : _bboxJson(logoBox!),
        'panel_bbox': autoPanelBox == null ? null : _bboxJson(autoPanelBox!),
        'feature_descriptor_path': null,
        'version': 1,
        'status': 'submitted',
        'created_at': now,
        'updated_at': now,
      },
      'buttons': <Object?>[
        for (final (int i, LabeledButtonBox b) in buttons.indexed)
          <String, Object?>{
            'id': 'btn_${autoTemplateCode}_${i + 1}',
            'template_id': autoTemplateId,
            'button_id': '${i + 1}',
            'label': b.name,
            'vietnamese_name': b.name,
            'function_description':
                b.usage.trim().isEmpty ? b.name : b.usage.trim(),
            'bbox_template_coordinates': _bboxJson(b.rect),
            'polygon_template_coordinates': null,
            'button_type': 'physical',
            'created_at': now,
            'updated_at': now,
          },
      ],
    };
  }

  // ---- actions ---------------------------------------------------------

  Future<void> _pickPhoto(ImageSource source) async {
    final XFile? file = await ImagePicker().pickImage(source: source);
    if (file == null) return;
    final Uint8List bytes = await file.readAsBytes();
    final ui.Image decoded = await decodeImageFromList(bytes);
    if (!mounted) return;
    setState(() {
      photo = bytes;
      photoSize = Size(decoded.width.toDouble(), decoded.height.toDouble());
      // New photo invalidates any boxes drawn on the previous one.
      logoBox = null;
      buttons = <LabeledButtonBox>[];
    });
  }

  Future<void> _submit() async {
    final Uint8List? bytes = photo;
    if (bytes == null || submitting) return;
    setState(() => submitting = true);
    try {
      await widget.backend.submitTemplate(
        imageBytes: bytes,
        brand: brandController.text.trim(),
        applianceType: effectiveApplianceType,
        buildLabels: _buildLabels,
      );
      if (!mounted) return;
      widget.onSave(autoDisplayName);
    } on FriendlyBackendException catch (error) {
      if (!mounted) return;
      setState(() => submitting = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.messageVi)),
      );
    } catch (error) {
      debugPrint('[SUBMIT] failed: $error');
      if (!mounted) return;
      setState(() => submitting = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Không gửi được. Vui lòng thử lại.')),
      );
    }
  }

  bool get _canGoNext => switch (step) {
        0 => photo != null,
        1 => brandController.text.trim().isNotEmpty &&
            (applianceType != 'other' ||
                customTypeController.text.trim().isNotEmpty),
        2 => logoBox != null && buttons.isNotEmpty,
        _ => true,
      };

  void _next() => setState(() => step += 1);
  void _prev() => setState(() => step -= 1);

  // ---- UI ---------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    return Column(
      children: <Widget>[
        AppHeader(
          title: 'Thêm thiết bị mới',
          subtitle: 'Gắn nhãn các nút bấm',
          onBack: () => step == 0 ? widget.onNavigate('back') : _prev(),
        ),
        StepperHeader(step: step),
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
            children: <Widget>[
              if (step == 0) _photoStep(),
              if (step == 1) _infoStep(),
              if (step == 2) _labelStep(),
              if (step == 3) _confirmStep(),
            ],
          ),
        ),
        FooterActions(
          column: step == 3,
          children: <Widget>[
            if (step < 3) ...<Widget>[
              if (step > 0)
                Expanded(
                  flex: 5,
                  child: NeutralButton(
                      label: 'Bước trước',
                      icon: Icons.arrow_back,
                      onTap: _prev),
                ),
              if (step > 0) const SizedBox(width: 10),
              Expanded(
                flex: 6,
                child: PrimaryButton(
                    label: 'Tiếp theo',
                    iconAfter: Icons.arrow_forward,
                    enabled: _canGoNext,
                    onTap: _next),
              ),
            ],
            if (step == 3) ...<Widget>[
              GreenButton(
                  label: submitting ? 'Đang gửi...' : 'Lưu thiết bị',
                  icon: Icons.check,
                  enabled: !submitting,
                  onTap: _submit),
              const SizedBox(height: 10),
              NeutralButton(label: 'Quay lại chỉnh sửa', onTap: _prev),
            ],
          ],
        ),
      ],
    );
  }

  Widget _photoStep() {
    return Column(
      children: <Widget>[
        const InfoCard(
            index: '1',
            title: 'Chụp ảnh mặt trước thiết bị',
            subtitle: 'Đảm bảo đủ ánh sáng, thấy rõ toàn bộ nút bấm'),
        const SizedBox(height: 16),
        if (photo != null) ...<Widget>[
          ClipRRect(
            borderRadius: BorderRadius.circular(14),
            child: Image.memory(photo!, fit: BoxFit.contain),
          ),
          const SizedBox(height: 12),
        ],
        Row(
          children: <Widget>[
            Expanded(
              child: NeutralButton(
                label: 'Chụp ảnh',
                icon: Icons.photo_camera,
                onTap: () => _pickPhoto(ImageSource.camera),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: NeutralButton(
                label: 'Chọn từ thư viện',
                icon: Icons.photo_library,
                onTap: () => _pickPhoto(ImageSource.gallery),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        const TipBox(),
      ],
    );
  }

  Widget _infoStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        const InfoCard(
            index: '2',
            title: 'Thông tin thiết bị',
            subtitle: 'Chỉ cần 3 thông tin, phần còn lại tự điền'),
        const SizedBox(height: 16),
        _fieldCard('HÃNG (bắt buộc)', brandController, 'VD: Electrolux'),
        const SizedBox(height: 12),
        const Text('LOẠI THIẾT BỊ',
            style: TextStyle(
                color: SilverTokens.ink2,
                fontSize: 13.5,
                fontWeight: FontWeight.w900)),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: <Widget>[
            for (final (String value, String labelVi) in kApplianceTypes)
              ChoiceChip(
                label: Text(labelVi,
                    style: const TextStyle(fontWeight: FontWeight.w900)),
                selected: applianceType == value,
                onSelected: (_) => setState(() => applianceType = value),
              ),
          ],
        ),
        if (applianceType == 'other') ...<Widget>[
          const SizedBox(height: 12),
          _fieldCard('LOẠI THIẾT BỊ KHÁC (bắt buộc)', customTypeController,
              'VD: Nồi chiên không dầu'),
        ],
        const SizedBox(height: 12),
        _fieldCard('MODEL (không bắt buộc)', modelController, 'VD: EWF9024'),
        if (!_canGoNext) ...<Widget>[
          const SizedBox(height: 10),
          Text(
            brandController.text.trim().isEmpty
                ? '⚠ Điền tên HÃNG để tiếp tục'
                : '⚠ Điền LOẠI THIẾT BỊ KHÁC để tiếp tục',
            style: const TextStyle(
                color: SilverTokens.red,
                fontSize: 15,
                fontWeight: FontWeight.w900),
          ),
        ],
        const SizedBox(height: 14),
        SilverCard(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const Text('Tự điền giúp ông/bà:',
                  style: TextStyle(
                      color: SilverTokens.ink2,
                      fontSize: 13,
                      fontWeight: FontWeight.w900)),
              const SizedBox(height: 6),
              Text('Tên: $autoDisplayName\nMã mẫu: $autoTemplateCode',
                  style: const TextStyle(
                      color: SilverTokens.ink,
                      fontSize: 14,
                      fontWeight: FontWeight.w700)),
            ],
          ),
        ),
      ],
    );
  }

  Widget _fieldCard(
      String label, TextEditingController controller, String hint) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(label,
            style: const TextStyle(
                color: SilverTokens.ink2,
                fontSize: 13.5,
                fontWeight: FontWeight.w900)),
        const SizedBox(height: 7),
        TextFormField(
          controller: controller,
          onChanged: (_) => setState(() {}),
          style: const TextStyle(
              color: SilverTokens.ink,
              fontSize: 18,
              fontWeight: FontWeight.w900),
          decoration: InputDecoration(
            hintText: hint,
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(13),
              borderSide:
                  const BorderSide(color: SilverTokens.blueTint2, width: 2),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(13),
              borderSide: const BorderSide(color: SilverTokens.blue, width: 2),
            ),
          ),
        ),
      ],
    );
  }

  Widget _labelStep() {
    final bool logoDone = logoBox != null;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        InfoCard(
            index: '3',
            title: logoDone
                ? 'Khoanh vùng từng NÚT bấm'
                : 'Khoanh vùng LOGO hãng trước',
            subtitle: logoDone
                ? 'Kéo tay trên ảnh để vẽ khung quanh mỗi nút'
                : 'Kéo tay trên ảnh để vẽ khung quanh logo hãng'),
        const SizedBox(height: 12),
        if (photo != null && photoSize != null)
          LabelCanvas(
            photo: photo!,
            photoSize: photoSize!,
            logoBox: logoBox,
            buttons: buttons,
            onBoxDrawn: (Rect rect) {
              setState(() {
                if (logoBox == null) {
                  logoBox = rect;
                } else {
                  buttons = <LabeledButtonBox>[
                    ...buttons,
                    LabeledButtonBox(
                        rect: rect, name: 'Nút ${buttons.length + 1}'),
                  ];
                }
              });
            },
          ),
        const SizedBox(height: 10),
        if (logoDone)
          NeutralButton(
            label: 'Vẽ lại logo',
            icon: Icons.refresh,
            compact: true,
            onTap: () => setState(() => logoBox = null),
          ),
        const SizedBox(height: 6),
        for (final (int i, LabeledButtonBox b) in buttons.indexed)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: SilverCard(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              child: Column(
                children: <Widget>[
                  Row(
                    children: <Widget>[
                      CircleAvatar(
                        radius: 15,
                        backgroundColor: SilverTokens.redSoft,
                        child: Text('${i + 1}',
                            style: const TextStyle(
                                color: SilverTokens.red,
                                fontSize: 14,
                                fontWeight: FontWeight.w900)),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: TextFormField(
                          initialValue: b.name,
                          onChanged: (String value) =>
                              setState(() => b.name = value),
                          style: const TextStyle(
                              color: SilverTokens.ink,
                              fontSize: 17,
                              fontWeight: FontWeight.w900),
                          decoration: const InputDecoration(
                              hintText: 'Tên nút',
                              border: InputBorder.none,
                              isDense: true),
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.delete_outline,
                            color: SilverTokens.red),
                        tooltip: 'Xoá nút này',
                        onPressed: () =>
                            setState(() => buttons = <LabeledButtonBox>[
                                  ...buttons.sublist(0, i),
                                  ...buttons.sublist(i + 1),
                                ]),
                      ),
                    ],
                  ),
                  Padding(
                    padding: const EdgeInsets.only(left: 42),
                    child: TextFormField(
                      initialValue: b.usage,
                      onChanged: (String value) =>
                          setState(() => b.usage = value),
                      minLines: 2,
                      maxLines: null,
                      keyboardType: TextInputType.multiline,
                      style: const TextStyle(
                          color: SilverTokens.ink2,
                          fontSize: 15,
                          height: 1.35,
                          fontWeight: FontWeight.w700),
                      decoration: InputDecoration(
                        hintText: 'Công dụng (VD: Bắt đầu chu trình giặt)',
                        isDense: true,
                        filled: true,
                        fillColor: SilverTokens.surface2,
                        contentPadding: const EdgeInsets.symmetric(
                            horizontal: 12, vertical: 10),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(10),
                          borderSide: BorderSide.none,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
      ],
    );
  }

  Widget _confirmStep() {
    return Column(
      children: <Widget>[
        const InfoCard(
            index: '4',
            title: 'Xác nhận và lưu',
            subtitle: 'Kiểm tra lại rồi gửi cho quản trị viên duyệt',
            tone: 'green'),
        const SizedBox(height: 16),
        SilverCard(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(autoDisplayName,
                  style: const TextStyle(
                      color: SilverTokens.ink,
                      fontSize: 19,
                      fontWeight: FontWeight.w900)),
              const SizedBox(height: 8),
              Text(
                'Mã mẫu: $autoTemplateCode\n'
                'Logo: ${logoBox == null ? "chưa có" : "đã khoanh"}\n'
                '${buttons.length} nút đã gắn nhãn',
                style: const TextStyle(
                    color: SilverTokens.ink2,
                    fontSize: 15,
                    height: 1.5,
                    fontWeight: FontWeight.w700),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

/// Photo with drag-to-draw labeling. Boxes are stored in image pixel
/// coordinates so the export matches the label web tool.
class LabelCanvas extends StatefulWidget {
  const LabelCanvas({
    required this.photo,
    required this.photoSize,
    required this.logoBox,
    required this.buttons,
    required this.onBoxDrawn,
    super.key,
  });

  final Uint8List photo;
  final Size photoSize;
  final Rect? logoBox;
  final List<LabeledButtonBox> buttons;
  final void Function(Rect rectInImagePixels) onBoxDrawn;

  @override
  State<LabelCanvas> createState() => _LabelCanvasState();
}

class _LabelCanvasState extends State<LabelCanvas> {
  Offset? _dragStart;
  Offset? _dragCurrent;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final double width = constraints.maxWidth;
        final double scale = width / widget.photoSize.width;
        final double height = widget.photoSize.height * scale;

        return GestureDetector(
          onPanStart: (DragStartDetails d) => setState(() {
            _dragStart = d.localPosition;
            _dragCurrent = d.localPosition;
          }),
          onPanUpdate: (DragUpdateDetails d) =>
              setState(() => _dragCurrent = d.localPosition),
          onPanEnd: (_) {
            final Offset? start = _dragStart;
            final Offset? end = _dragCurrent;
            setState(() {
              _dragStart = null;
              _dragCurrent = null;
            });
            if (start == null || end == null) return;
            final Rect widgetRect = Rect.fromPoints(start, end);
            // Ignore accidental taps: box must be meaningfully sized.
            if (widgetRect.width < 12 || widgetRect.height < 12) return;
            final Rect imageRect = Rect.fromLTRB(
              (widgetRect.left / scale).clamp(0.0, widget.photoSize.width),
              (widgetRect.top / scale).clamp(0.0, widget.photoSize.height),
              (widgetRect.right / scale).clamp(0.0, widget.photoSize.width),
              (widgetRect.bottom / scale).clamp(0.0, widget.photoSize.height),
            );
            widget.onBoxDrawn(imageRect);
          },
          child: ClipRRect(
            borderRadius: BorderRadius.circular(14),
            child: SizedBox(
              width: width,
              height: height,
              child: Stack(
                fit: StackFit.expand,
                children: <Widget>[
                  Image.memory(widget.photo, fit: BoxFit.fill),
                  CustomPaint(
                    painter: _LabelCanvasPainter(
                      scale: scale,
                      logoBox: widget.logoBox,
                      buttons: widget.buttons,
                      dragRect: _dragStart != null && _dragCurrent != null
                          ? Rect.fromPoints(_dragStart!, _dragCurrent!)
                          : null,
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _LabelCanvasPainter extends CustomPainter {
  _LabelCanvasPainter({
    required this.scale,
    required this.logoBox,
    required this.buttons,
    required this.dragRect,
  });

  final double scale;
  final Rect? logoBox;
  final List<LabeledButtonBox> buttons;

  /// In-progress drag, already in widget coordinates.
  final Rect? dragRect;

  Rect _toWidget(Rect r) => Rect.fromLTRB(
      r.left * scale, r.top * scale, r.right * scale, r.bottom * scale);

  void _drawBox(Canvas canvas, Rect rect, Color color, String tag) {
    canvas.drawRect(
      rect,
      Paint()
        ..style = PaintingStyle.fill
        ..color = color.withValues(alpha: 0.15),
    );
    canvas.drawRect(
      rect,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2
        ..color = color,
    );
    final TextPainter text = TextPainter(
      text: TextSpan(
        text: tag,
        style: TextStyle(
          color: Colors.white,
          fontSize: 12,
          fontWeight: FontWeight.w900,
          backgroundColor: color,
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    text.paint(canvas, rect.topLeft + const Offset(2, 2));
  }

  @override
  void paint(Canvas canvas, Size size) {
    if (logoBox != null) {
      _drawBox(canvas, _toWidget(logoBox!), SilverTokens.blue, 'LOGO');
    }
    for (final (int i, LabeledButtonBox b) in buttons.indexed) {
      _drawBox(canvas, _toWidget(b.rect), SilverTokens.red, '${i + 1}');
    }
    if (dragRect != null) {
      canvas.drawRect(
        dragRect!,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2
          ..color = SilverTokens.green,
      );
    }
  }

  @override
  bool shouldRepaint(_LabelCanvasPainter oldDelegate) =>
      oldDelegate.logoBox != logoBox ||
      oldDelegate.buttons != buttons ||
      oldDelegate.dragRect != dragRect ||
      oldDelegate.scale != scale;
}

class DevicesScreen extends StatelessWidget {
  const DevicesScreen({
    required this.devices,
    required this.onNavigate,
    super.key,
  });

  final List<DemoDevice> devices;
  final void Function(String target, {DemoDevice? device}) onNavigate;

  @override
  Widget build(BuildContext context) {
    final bool isEmpty = devices.isEmpty;
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 18),
      children: <Widget>[
        Row(
          children: <Widget>[
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  const Text(
                    'Thiết bị của tôi',
                    style: TextStyle(
                      color: SilverTokens.ink,
                      fontSize: 27,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 5),
                  Text(
                    '${devices.length} thiết bị đã lưu',
                    style: const TextStyle(
                      color: SilverTokens.ink2,
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            ),
            SmallPrimaryButton(
                label: 'Thêm', icon: Icons.add, onTap: () => onNavigate('add')),
          ],
        ),
        const SizedBox(height: 20),
        if (isEmpty)
          const _EmptyDeviceState(
            title: 'Danh sách còn trống',
            subtitle: 'Thiết bị bạn đã dùng sẽ xuất hiện ở đây.',
          )
        else
          ...devices.map(
            (DemoDevice device) => Padding(
              padding: const EdgeInsets.only(bottom: 14),
              child: DeviceCard(
                device: device,
                onOpen: () => onNavigate('voice', device: device),
              ),
            ),
          ),
        SecondaryDashedButton(
          label: 'Thêm thiết bị mới',
          icon: Icons.add,
          onTap: () => onNavigate('add'),
        ),
      ],
    );
  }
}

class _EmptyDeviceState extends StatelessWidget {
  const _EmptyDeviceState({required this.title, required this.subtitle});

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return SilverCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            title,
            style: const TextStyle(
              color: SilverTokens.ink,
              fontSize: 18,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            subtitle,
            style: const TextStyle(
              color: SilverTokens.ink2,
              fontSize: 15,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({required this.onNavigate, super.key});

  final void Function(String target, {DemoDevice? device}) onNavigate;

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  int size = 1;
  bool readAloud = true;
  bool contrast = false;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: <Widget>[
        AppHeader(
          title: 'Cài đặt',
          subtitle: 'Tuỳ chỉnh cho dễ dùng hơn',
          onBack: () => widget.onNavigate('back'),
        ),
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 6, 20, 18),
            children: <Widget>[
              SilverCard(
                padding:
                    const EdgeInsets.symmetric(horizontal: 18, vertical: 4),
                child: Column(
                  children: <Widget>[
                    SettingsRow(
                      icon: const Text('A',
                          style: TextStyle(
                              fontSize: 17,
                              fontWeight: FontWeight.w900,
                              color: SilverTokens.blue)),
                      title: 'Cỡ chữ',
                      subtitle: 'Chữ to dễ đọc hơn',
                      control: SegmentedTextSize(
                          value: size,
                          onChange: (int next) => setState(() => size = next)),
                    ),
                    SettingsRow(
                      icon:
                          const Icon(Icons.volume_up, color: SilverTokens.blue),
                      title: 'Đọc to hướng dẫn',
                      subtitle: 'Nghe từng bước bằng giọng nói',
                      control: Switch(
                        value: readAloud,
                        activeThumbColor: Colors.white,
                        activeTrackColor: SilverTokens.green,
                        onChanged: (bool next) =>
                            setState(() => readAloud = next),
                      ),
                    ),
                    SettingsRow(
                      last: true,
                      icon:
                          const Icon(Icons.wb_sunny, color: SilverTokens.blue),
                      title: 'Độ tương phản cao',
                      subtitle: 'Màu rõ nét, dễ nhìn',
                      control: Switch(
                        value: contrast,
                        activeThumbColor: Colors.white,
                        activeTrackColor: SilverTokens.green,
                        onChanged: (bool next) =>
                            setState(() => contrast = next),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 18),
              GreenButton(
                  label: 'Lưu cài đặt',
                  icon: Icons.check,
                  onTap: () => widget.onNavigate('back')),
            ],
          ),
        ),
      ],
    );
  }
}

class AppHeader extends StatelessWidget {
  const AppHeader({
    required this.title,
    required this.onBack,
    this.subtitle,
    super.key,
  });

  final String title;
  final String? subtitle;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 12),
      child: Row(
        children: <Widget>[
          IconRoundButton(icon: Icons.chevron_left, onTap: onBack),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  title,
                  style: const TextStyle(
                    color: SilverTokens.ink,
                    fontSize: 20,
                    height: 1.15,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                if (subtitle != null)
                  Text(
                    subtitle!,
                    style: const TextStyle(
                      color: SilverTokens.ink2,
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class DarkDeviceHeader extends StatelessWidget {
  const DarkDeviceHeader({
    required this.device,
    required this.trailing,
    required this.onBack,
    super.key,
  });

  final DemoDevice device;
  final Widget trailing;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 12),
      child: Row(
        children: <Widget>[
          IconRoundButton(icon: Icons.chevron_left, dark: true, onTap: onBack),
          const SizedBox(width: 12),
          const CircleAvatar(
              backgroundColor: SilverTokens.greenBright, radius: 5),
          const SizedBox(width: 9),
          Expanded(
            child: Text(
              '${device.name} - ${device.short}',
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 17,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
          const SizedBox(width: 8),
          trailing,
        ],
      ),
    );
  }
}

class IconRoundButton extends StatelessWidget {
  const IconRoundButton({
    required this.icon,
    required this.onTap,
    this.dark = false,
    super.key,
  });

  final IconData icon;
  final VoidCallback onTap;
  final bool dark;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: dark ? Colors.white.withValues(alpha: 0.12) : SilverTokens.surface,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: SizedBox(
          width: 46,
          height: 46,
          child: Icon(icon,
              color: dark ? Colors.white : SilverTokens.ink, size: 28),
        ),
      ),
    );
  }
}

class SettingsButton extends StatelessWidget {
  const SettingsButton({required this.onTap, super.key});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: SilverTokens.surface,
      borderRadius: BorderRadius.circular(18),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(18),
        child: const SizedBox(
          width: 64,
          height: 64,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              Icon(Icons.wb_sunny, color: SilverTokens.blue, size: 24),
              SizedBox(height: 3),
              Text(
                'Cài đặt',
                style: TextStyle(
                    color: SilverTokens.ink2,
                    fontSize: 12,
                    fontWeight: FontWeight.w900),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class BigStartButton extends StatelessWidget {
  const BigStartButton({required this.onTap, super.key});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(24),
          gradient: const LinearGradient(
            colors: <Color>[SilverTokens.blueBright, SilverTokens.blueDeep],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          boxShadow: <BoxShadow>[
            BoxShadow(
              color: SilverTokens.blueDeep.withValues(alpha: 0.32),
              blurRadius: 26,
              offset: const Offset(0, 12),
            ),
          ],
        ),
        child: Row(
          children: <Widget>[
            Container(
              width: 62,
              height: 62,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.18),
                borderRadius: BorderRadius.circular(18),
              ),
              child:
                  const Icon(Icons.photo_camera, color: Colors.white, size: 32),
            ),
            const SizedBox(width: 16),
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Bắt đầu hướng dẫn',
                    style: TextStyle(
                        color: Colors.white,
                        fontSize: 22,
                        fontWeight: FontWeight.w900),
                  ),
                  SizedBox(height: 3),
                  Text(
                    'Camera tự nhận diện nút bấm',
                    style: TextStyle(
                        color: Color(0xDDFFFFFF),
                        fontSize: 15,
                        fontWeight: FontWeight.w700),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Single flat info block summarizing the 3 usage steps.
///
/// Intentionally NOT interactive: no InkWell/onTap, no drop shadow, header
/// label + vertical timeline so it reads as a description, not tappable rows.
class HowToHintCard extends StatelessWidget {
  const HowToHintCard({required this.steps, super.key});

  final List<String> steps;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(18, 16, 18, 18),
      decoration: BoxDecoration(
        color: SilverTokens.surface2,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: SilverTokens.blueTint, width: 1.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Text(
            '3 bước đơn giản',
            style: TextStyle(
              color: SilverTokens.ink2,
              fontSize: 14,
              fontWeight: FontWeight.w900,
              letterSpacing: 0.3,
            ),
          ),
          const SizedBox(height: 14),
          ...steps.indexed.map((entry) {
            final bool last = entry.$1 == steps.length - 1;
            return IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Column(
                    children: <Widget>[
                      Container(
                        width: 26,
                        height: 26,
                        alignment: Alignment.center,
                        decoration: const BoxDecoration(
                          shape: BoxShape.circle,
                          color: SilverTokens.blueTint2,
                        ),
                        child: Text(
                          '${entry.$1 + 1}',
                          style: const TextStyle(
                            color: SilverTokens.blueDeep,
                            fontSize: 14,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ),
                      if (!last)
                        Expanded(
                          child: Container(
                            width: 2,
                            color: SilverTokens.blueTint2,
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(width: 13),
                  Expanded(
                    child: Padding(
                      padding: EdgeInsets.only(top: 3, bottom: last ? 0 : 16),
                      child: Text(
                        entry.$2,
                        style: const TextStyle(
                          color: SilverTokens.ink,
                          fontSize: 16,
                          height: 1.2,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }
}

class SilverCard extends StatelessWidget {
  const SilverCard({
    required this.child,
    this.padding = const EdgeInsets.all(14),
    super.key,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: SilverTokens.surface,
        borderRadius: BorderRadius.circular(22),
        boxShadow: const <BoxShadow>[
          BoxShadow(
              color: Color(0x12203456), blurRadius: 22, offset: Offset(0, 6)),
        ],
      ),
      child: child,
    );
  }
}

class DeviceRow extends StatelessWidget {
  const DeviceRow({
    required this.device,
    required this.onTap,
    super.key,
  });

  final DemoDevice device;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(22),
        child: SilverCard(
          child: Row(
            children: <Widget>[
              DeviceGlyph(kind: device.kind, tone: device.tone),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      device.name,
                      style: const TextStyle(
                          color: SilverTokens.ink,
                          fontSize: 18,
                          fontWeight: FontWeight.w900),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Mẫu: ${device.model}',
                      style: const TextStyle(
                          color: SilverTokens.ink2,
                          fontSize: 13.5,
                          fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 5),
                    Row(
                      children: <Widget>[
                        const CircleAvatar(
                            backgroundColor: SilverTokens.green, radius: 4.5),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            'Dùng lần cuối: ${device.last}',
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                                color: SilverTokens.green,
                                fontSize: 12.5,
                                fontWeight: FontWeight.w800),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, color: SilverTokens.ink3),
            ],
          ),
        ),
      ),
    );
  }
}

class DeviceCard extends StatelessWidget {
  const DeviceCard({
    required this.device,
    required this.onOpen,
    super.key,
  });

  final DemoDevice device;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    return Container(
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: SilverTokens.surface,
        borderRadius: BorderRadius.circular(22),
        boxShadow: const <BoxShadow>[
          BoxShadow(
              color: Color(0x12203456), blurRadius: 22, offset: Offset(0, 6)),
        ],
      ),
      child: Column(
        children: <Widget>[
          Container(height: 5, color: toneColor(device.tone)),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: <Widget>[
                DeviceGlyph(kind: device.kind, tone: device.tone),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(device.name,
                          style: const TextStyle(
                              color: SilverTokens.ink,
                              fontSize: 18,
                              fontWeight: FontWeight.w900)),
                      const SizedBox(height: 2),
                      Text('Mẫu: ${device.model}',
                          style: const TextStyle(
                              color: SilverTokens.ink2,
                              fontSize: 13.5,
                              fontWeight: FontWeight.w700)),
                      const SizedBox(height: 5),
                      Row(
                        children: <Widget>[
                          const Icon(Icons.schedule,
                              size: 14, color: SilverTokens.ink3),
                          const SizedBox(width: 5),
                          Text(device.last,
                              style: const TextStyle(
                                  color: SilverTokens.ink3,
                                  fontSize: 13,
                                  fontWeight: FontWeight.w700)),
                        ],
                      ),
                    ],
                  ),
                ),
                OpenDeviceButton(tone: device.tone, onTap: onOpen),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class DeviceGlyph extends StatelessWidget {
  const DeviceGlyph({
    required this.kind,
    required this.tone,
    this.size = 52,
    super.key,
  });

  final String kind;
  final String tone;
  final double size;

  @override
  Widget build(BuildContext context) {
    final IconData icon = switch (kind) {
      'tv' => Icons.tv,
      'ac' => Icons.ac_unit,
      'fryer' => Icons.local_fire_department,
      _ => Icons.devices,
    };
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
          color: toneTint(tone), borderRadius: BorderRadius.circular(15)),
      child: Icon(icon, color: toneColor(tone), size: size * 0.55),
    );
  }
}

class OpenDeviceButton extends StatelessWidget {
  const OpenDeviceButton({required this.tone, required this.onTap, super.key});

  final String tone;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: toneTint(tone),
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: SizedBox(
          width: 54,
          height: 54,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              Icon(Icons.visibility, color: toneColor(tone), size: 22),
              Text('Mở',
                  style: TextStyle(
                      color: toneColor(tone),
                      fontSize: 11,
                      fontWeight: FontWeight.w900)),
            ],
          ),
        ),
      ),
    );
  }
}

class CameraCard extends StatefulWidget {
  const CameraCard({required this.scanning, super.key});

  final bool scanning;

  @override
  State<CameraCard> createState() => _CameraCardState();
}

class _CameraCardState extends State<CameraCard> {
  CameraController? _cameraController;
  late Future<void> _cameraInitialization;

  @override
  void initState() {
    super.initState();
    _cameraInitialization = _initializeCamera();
  }

  Future<void> _initializeCamera() async {
    final cameras = await availableCameras();
    if (cameras.isEmpty) {
      throw CameraException('no_camera', 'No camera was found on this device.');
    }

    final camera = cameras.firstWhere(
      (description) => description.lensDirection == CameraLensDirection.back,
      orElse: () => cameras.first,
    );

    final controller = CameraController(
      camera,
      ResolutionPreset.medium,
      enableAudio: false,
    );
    await controller.initialize();

    if (!mounted) {
      await controller.dispose();
      return;
    }

    setState(() {
      _cameraController = controller;
    });
  }

  @override
  void dispose() {
    unawaited(_cameraController?.dispose());
    super.dispose();
  }

  /// Grab one still frame for recognition; null when the camera never
  /// initialized (desktop dev, denied permission) so callers can fall back.
  Future<Uint8List?> captureFrame() async {
    final controller = _cameraController;
    if (controller == null || !controller.value.isInitialized) {
      return null;
    }
    try {
      final XFile shot = await controller.takePicture();
      return await shot.readAsBytes();
    } catch (e) {
      debugPrint('[CAMERA] capture failed: $e');
      return null;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 18),
      decoration: BoxDecoration(
        color: const Color(0xFF0C1117),
        borderRadius: BorderRadius.circular(22),
      ),
      child: Column(
        children: <Widget>[
          const Text(
            'Đưa mặt trước thiết bị vào khung',
            style: TextStyle(
                color: Colors.white,
                fontSize: 14.5,
                fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 12),
          LayoutBuilder(
            builder: (context, constraints) {
              final previewHeight =
                  (constraints.maxWidth * 9 / 16).clamp(300.0, 460.0);
              return FutureBuilder<void>(
                future: _cameraInitialization,
                builder: (context, snapshot) {
                  if (snapshot.connectionState != ConnectionState.done ||
                      snapshot.hasError ||
                      _cameraController == null) {
                    return RemotePanel(
                      display: '26°C',
                      scanning: widget.scanning,
                      height: previewHeight,
                    );
                  }

                  return CameraPreviewPanel(
                    controller: _cameraController!,
                    scanning: widget.scanning,
                    height: previewHeight,
                  );
                },
              );
            },
          ),
        ],
      ),
    );
  }
}

class CameraPreviewPanel extends StatelessWidget {
  const CameraPreviewPanel({
    required this.controller,
    required this.scanning,
    required this.height,
    super.key,
  });

  final CameraController controller;
  final bool scanning;
  final double height;

  @override
  Widget build(BuildContext context) {
    // Sensor preview is reported width-by-height of the raw frame; swap so the
    // FittedBox source keeps the true aspect ratio regardless of orientation.
    final previewSize = controller.value.previewSize;
    final double srcWidth = previewSize?.height ?? 305;
    final double srcHeight = previewSize?.width ?? 305;

    return ClipRRect(
      borderRadius: BorderRadius.circular(18),
      child: SizedBox(
        height: height,
        width: double.infinity,
        child: Stack(
          fit: StackFit.expand,
          children: <Widget>[
            FittedBox(
              fit: BoxFit.cover,
              child: SizedBox(
                width: srcWidth,
                height: srcHeight,
                child: CameraPreview(controller),
              ),
            ),
            if (scanning) const ScanFrame(),
          ],
        ),
      ),
    );
  }
}

class RemotePanel extends StatelessWidget {
  const RemotePanel({
    required this.display,
    this.height = 300,
    this.scanning = false,
    this.highlight,
    this.showArrow = false,
    super.key,
  });

  final String display;
  final double height;
  final bool scanning;
  final String? highlight;
  final bool showArrow;

  @override
  Widget build(BuildContext context) {
    final List<RemoteButtonData> buttons = <RemoteButtonData>[
      const RemoteButtonData('power', 'Nguồn', 0.70, 0.06, 0.24, 0.22,
          round: true),
      const RemoteButtonData('tempdn', 'Nhiệt độ -', 0.08, 0.33, 0.36, 0.19),
      const RemoteButtonData('tempup', 'Nhiệt độ +', 0.56, 0.33, 0.36, 0.19),
      const RemoteButtonData('mode', 'Chế độ', 0.08, 0.59, 0.36, 0.17),
      const RemoteButtonData('fan', 'Quạt', 0.56, 0.59, 0.36, 0.17),
      const RemoteButtonData('timer', 'Hẹn giờ', 0.32, 0.83, 0.36, 0.15),
    ];
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final double width = constraints.maxWidth;
        return Container(
          height: height,
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: <Color>[Color(0xFF222A33), Color(0xFF171D24)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
          ),
          child: Stack(
            clipBehavior: Clip.hardEdge,
            children: <Widget>[
              Positioned(
                left: width * 0.08,
                top: height * 0.05,
                width: width * 0.46,
                height: height * 0.15,
                child: Container(
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                      color: const Color(0xFF0C1116),
                      borderRadius: BorderRadius.circular(8)),
                  child: Text(
                    display,
                    style: const TextStyle(
                      color: Color(0xFF37D98A),
                      fontSize: 22,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 1,
                    ),
                  ),
                ),
              ),
              for (final RemoteButtonData button in buttons)
                Positioned(
                  left: width * button.x,
                  top: height * button.y,
                  width: width * button.w,
                  height: height * button.h,
                  child: RemoteButtonMarker(
                    data: button,
                    active: highlight == button.id,
                    showArrow: showArrow && highlight == button.id,
                  ),
                ),
              if (scanning) const ScanFrame(),
            ],
          ),
        );
      },
    );
  }
}

class TemplateDataPanel extends StatefulWidget {
  const TemplateDataPanel({
    required this.template,
    this.activeButtonId,
    super.key,
  });

  final TemplateDetailDto template;
  final String? activeButtonId;

  @override
  State<TemplateDataPanel> createState() => _TemplateDataPanelState();
}

class _TemplateDataPanelState extends State<TemplateDataPanel> {
  /// Button bboxes are in template-image pixel coordinates, so scaling needs
  /// the image's true size. Resolved from the downloaded image; until then a
  /// max-bbox-extent estimate keeps the layout from jumping too far.
  Size? _resolvedImageSize;
  ImageStream? _imageStream;
  ImageStreamListener? _imageListener;

  @override
  void initState() {
    super.initState();
    _resolveImageSize();
  }

  @override
  void didUpdateWidget(TemplateDataPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.template.templateImageUrl !=
        widget.template.templateImageUrl) {
      _resolvedImageSize = null;
      _resolveImageSize();
    }
  }

  void _resolveImageSize() {
    _detachImageListener();
    final ImageStream stream = NetworkImage(
      '$defaultSilverTechApiBaseUrl/${widget.template.templateImageUrl}',
      headers: apiRequestHeaders,
    ).resolve(ImageConfiguration.empty);
    final ImageStreamListener listener = ImageStreamListener(
      (ImageInfo info, bool _) {
        if (!mounted) return;
        setState(() {
          _resolvedImageSize = Size(
            info.image.width.toDouble(),
            info.image.height.toDouble(),
          );
        });
      },
      onError: (Object _, StackTrace? __) {},
    );
    _imageStream = stream;
    _imageListener = listener;
    stream.addListener(listener);
  }

  void _detachImageListener() {
    final ImageStream? stream = _imageStream;
    final ImageStreamListener? listener = _imageListener;
    if (stream != null && listener != null) {
      stream.removeListener(listener);
    }
    _imageStream = null;
    _imageListener = null;
  }

  @override
  void dispose() {
    _detachImageListener();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final TemplateDetailDto template = widget.template;
    final String? activeButtonId = widget.activeButtonId;
    final List<TemplateButtonDto> buttons = template.buttons;
    final Size imageSize = _resolvedImageSize ?? _templateImageSize(template);
    final double sourceWidth = imageSize.width;
    final double sourceHeight = imageSize.height;

    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final double width = constraints.maxWidth;
        final double panelHeight = width * sourceHeight / sourceWidth;
        final double scale = width / sourceWidth;

        return Container(
          height: panelHeight,
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: <Color>[Color(0xFF222A33), Color(0xFF171D24)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
          ),
          child: Stack(
            clipBehavior: Clip.hardEdge,
            children: <Widget>[
              Positioned.fill(
                child: Image.network(
                  '$defaultSilverTechApiBaseUrl/${template.templateImageUrl}',
                  headers: apiRequestHeaders,
                  fit: BoxFit.fill,
                  errorBuilder: (BuildContext context, Object error,
                      StackTrace? stackTrace) {
                    return const SizedBox.shrink();
                  },
                ),
              ),
              Positioned.fill(
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: Colors.black.withValues(alpha: 0.24),
                  ),
                ),
              ),
              Positioned(
                left: 16,
                top: 12,
                right: 16,
                child: Text(
                  '${template.brand} • ${template.buttons.length} nút từ DB',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Color(0xFFE9EEF4),
                    fontSize: 13,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
              for (final TemplateButtonDto button in buttons)
                Positioned(
                  left: button.bbox.x * scale,
                  top: button.bbox.y * scale,
                  width: button.bbox.width * scale,
                  height: button.bbox.height * scale,
                  child: _TemplateButtonBox(
                    button: button,
                    active: activeButtonId == button.buttonId,
                  ),
                ),
            ],
          ),
        );
      },
    );
  }
}

/// Shows the user's own captured/uploaded frame with the button quads the
/// vision service projected onto it — same view as the vision debugger.
class FrameOverlayPanel extends StatefulWidget {
  const FrameOverlayPanel({
    required this.frameBytes,
    required this.projectedButtons,
    this.logoFrameBox,
    required this.template,
    this.activeButtonId,
    super.key,
  });

  final Uint8List frameBytes;

  /// button_id -> 4 corners in frame pixel coordinates.
  final Map<String, List<ProjectedPoint>> projectedButtons;

  /// Detected brand logo box in frame pixel coordinates; widens the crop so
  /// the logo end of the panel stays visible.
  final LogoFrameBox? logoFrameBox;
  final TemplateDetailDto template;
  final String? activeButtonId;

  @override
  State<FrameOverlayPanel> createState() => _FrameOverlayPanelState();
}

class _FrameOverlayPanelState extends State<FrameOverlayPanel> {
  /// Quads are in frame pixel coordinates, so drawing needs the frame's
  /// true pixel size.
  Size? _frameSize;

  @override
  void initState() {
    super.initState();
    _resolveFrameSize();
  }

  @override
  void didUpdateWidget(FrameOverlayPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!identical(oldWidget.frameBytes, widget.frameBytes)) {
      _frameSize = null;
      _resolveFrameSize();
    }
  }

  Future<void> _resolveFrameSize() async {
    final Uint8List bytes = widget.frameBytes;
    final ui.Image image = await decodeImageFromList(bytes);
    if (!mounted || !identical(bytes, widget.frameBytes)) return;
    setState(() {
      _frameSize = Size(image.width.toDouble(), image.height.toDouble());
    });
  }

  String _labelFor(String buttonId) {
    for (final TemplateButtonDto button in widget.template.buttons) {
      if (button.buttonId == buttonId) {
        return button.vietnameseName.isNotEmpty
            ? button.vietnameseName
            : button.label;
      }
    }
    return buttonId;
  }

  /// Region of the frame to show: bounding rect of every projected button
  /// quad plus the detected logo box, plus a margin, clamped to the frame.
  /// Approximates the appliance panel so the user isn't shown the whole room
  /// around it.
  Rect _panelCrop(Size frameSize) {
    double minX = double.infinity, minY = double.infinity;
    double maxX = double.negativeInfinity, maxY = double.negativeInfinity;
    for (final List<ProjectedPoint> quad in widget.projectedButtons.values) {
      for (final ProjectedPoint p in quad) {
        if (p.x < minX) minX = p.x;
        if (p.y < minY) minY = p.y;
        if (p.x > maxX) maxX = p.x;
        if (p.y > maxY) maxY = p.y;
      }
    }
    final LogoFrameBox? logo = widget.logoFrameBox;
    if (logo != null) {
      if (logo.left < minX) minX = logo.left;
      if (logo.top < minY) minY = logo.top;
      if (logo.right > maxX) maxX = logo.right;
      if (logo.bottom > maxY) maxY = logo.bottom;
    }
    if (minX >= maxX || minY >= maxY) {
      return Rect.fromLTWH(0, 0, frameSize.width, frameSize.height);
    }
    final double marginX = (maxX - minX) * 0.10;
    final double marginY = (maxY - minY) * 0.10;
    final double left = (minX - marginX).clamp(0.0, frameSize.width);
    final double top = (minY - marginY).clamp(0.0, frameSize.height);
    final double right = (maxX + marginX).clamp(0.0, frameSize.width);
    final double bottom = (maxY + marginY).clamp(0.0, frameSize.height);
    return Rect.fromLTRB(left, top, right, bottom);
  }

  @override
  Widget build(BuildContext context) {
    final Size? frameSize = _frameSize;
    if (frameSize == null) {
      return const SizedBox(
        height: 220,
        child: Center(child: CircularProgressIndicator()),
      );
    }
    final Rect crop = _panelCrop(frameSize);
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final double width = constraints.maxWidth;
        final double height = width * crop.height / crop.width;
        final double scale = width / crop.width;

        return ClipRRect(
          borderRadius: BorderRadius.circular(18),
          child: SizedBox(
            width: width,
            height: height,
            child: Stack(
              clipBehavior: Clip.hardEdge,
              children: <Widget>[
                // Full frame scaled so the crop region fills the viewport;
                // everything outside is clipped away.
                Positioned(
                  left: -crop.left * scale,
                  top: -crop.top * scale,
                  width: frameSize.width * scale,
                  height: frameSize.height * scale,
                  child: Image.memory(widget.frameBytes, fit: BoxFit.fill),
                ),
                Positioned.fill(
                  child: CustomPaint(
                    painter: _ButtonQuadPainter(
                      projectedButtons: widget.projectedButtons,
                      scale: scale,
                      origin: crop.topLeft,
                      activeButtonId: widget.activeButtonId,
                      labelFor: _labelFor,
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _ButtonQuadPainter extends CustomPainter {
  _ButtonQuadPainter({
    required this.projectedButtons,
    required this.scale,
    this.origin = Offset.zero,
    required this.activeButtonId,
    required this.labelFor,
  });

  final Map<String, List<ProjectedPoint>> projectedButtons;
  final double scale;

  /// Top-left of the visible crop in frame pixel coordinates.
  final Offset origin;
  final String? activeButtonId;
  final String Function(String buttonId) labelFor;

  @override
  void paint(Canvas canvas, Size size) {
    projectedButtons.forEach((String buttonId, List<ProjectedPoint> quad) {
      if (quad.length < 3) return;
      final bool active = buttonId == activeButtonId;
      final Color color = active ? SilverTokens.green : SilverTokens.red;

      Offset map(ProjectedPoint p) =>
          Offset((p.x - origin.dx) * scale, (p.y - origin.dy) * scale);

      final Path path = Path()..moveTo(map(quad.first).dx, map(quad.first).dy);
      for (final ProjectedPoint point in quad.skip(1)) {
        path.lineTo(map(point).dx, map(point).dy);
      }
      path.close();

      canvas.drawPath(
        path,
        Paint()
          ..style = PaintingStyle.fill
          ..color = color.withValues(alpha: active ? 0.30 : 0.12),
      );
      canvas.drawPath(
        path,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = active ? 3 : 1.6
          ..color = color,
      );

      // Only the active button gets a label so the overlay stays readable
      // for elderly users; idle quads are outlines only.
      if (active) {
        final TextPainter text = TextPainter(
          text: TextSpan(
            text: labelFor(buttonId),
            style: const TextStyle(
              color: Colors.white,
              fontSize: 13,
              fontWeight: FontWeight.w900,
              backgroundColor: Color(0xCC0C1116),
            ),
          ),
          textDirection: TextDirection.ltr,
          maxLines: 1,
          ellipsis: '…',
        )..layout(maxWidth: size.width);
        final Rect bounds = path.getBounds();
        final double dx = (bounds.center.dx - text.width / 2)
            .clamp(0, size.width - text.width);
        final double dy =
            (bounds.top - text.height - 2).clamp(0, size.height - text.height);
        text.paint(canvas, Offset(dx, dy));
      }
    });
  }

  @override
  bool shouldRepaint(_ButtonQuadPainter oldDelegate) =>
      oldDelegate.projectedButtons != projectedButtons ||
      oldDelegate.scale != scale ||
      oldDelegate.origin != origin ||
      oldDelegate.activeButtonId != activeButtonId;
}

Size _templateImageSize(TemplateDetailDto template) {
  if (template.id == demoTemplateId) {
    return const Size(5712, 4284);
  }
  final double maxX = template.buttons
      .map((TemplateButtonDto button) => button.bbox.x + button.bbox.width)
      .fold<double>(1, (double a, double b) => a > b ? a : b);
  final double maxY = template.buttons
      .map((TemplateButtonDto button) => button.bbox.y + button.bbox.height)
      .fold<double>(1, (double a, double b) => a > b ? a : b);
  return Size(maxX, maxY);
}

class _TemplateButtonBox extends StatelessWidget {
  const _TemplateButtonBox({required this.button, required this.active});

  final TemplateButtonDto button;
  final bool active;

  @override
  Widget build(BuildContext context) {
    final String label =
        button.vietnameseName.isNotEmpty ? button.vietnameseName : button.label;
    return Container(
      alignment: Alignment.center,
      padding: const EdgeInsets.symmetric(horizontal: 3, vertical: 2),
      decoration: BoxDecoration(
        color: (active ? SilverTokens.green : SilverTokens.red)
            .withValues(alpha: active ? 0.32 : 0.14),
        border: Border.all(
          color: active ? SilverTokens.green : SilverTokens.red,
          width: active ? 2.2 : 1.4,
        ),
        borderRadius: BorderRadius.circular(6),
      ),
      child: FittedBox(
        fit: BoxFit.scaleDown,
        child: Text(
          label,
          textAlign: TextAlign.center,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 11,
            fontWeight: FontWeight.w900,
          ),
        ),
      ),
    );
  }
}

class RemoteButtonData {
  const RemoteButtonData(this.id, this.label, this.x, this.y, this.w, this.h,
      {this.round = false});

  final String id;
  final String label;
  final double x;
  final double y;
  final double w;
  final double h;
  final bool round;
}

class RemoteButtonMarker extends StatelessWidget {
  const RemoteButtonMarker({
    required this.data,
    required this.active,
    required this.showArrow,
    super.key,
  });

  final RemoteButtonData data;
  final bool active;
  final bool showArrow;

  @override
  Widget build(BuildContext context) {
    return Stack(
      clipBehavior: Clip.none,
      children: <Widget>[
        Positioned(
          top: -11,
          left: 0,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: active ? SilverTokens.green : SilverTokens.red,
              borderRadius: BorderRadius.circular(5),
            ),
            child: Text(
              data.label,
              style: const TextStyle(
                  color: Colors.white,
                  fontSize: 9.5,
                  fontWeight: FontWeight.w900),
            ),
          ),
        ),
        Positioned.fill(
          child: Container(
            decoration: BoxDecoration(
              color: active
                  ? SilverTokens.greenBright.withValues(alpha: 0.14)
                  : Colors.white.withValues(alpha: 0.03),
              borderRadius: BorderRadius.circular(data.round ? 999 : 9),
              border: Border.all(
                color: active
                    ? SilverTokens.greenBright
                    : SilverTokens.red.withValues(alpha: 0.85),
                width: 2,
              ),
              boxShadow: active
                  ? <BoxShadow>[
                      BoxShadow(
                          color:
                              SilverTokens.greenBright.withValues(alpha: 0.55),
                          blurRadius: 18),
                    ]
                  : const <BoxShadow>[],
            ),
          ),
        ),
        if (showArrow)
          const Positioned(
            right: -4,
            bottom: -18,
            child: Icon(Icons.arrow_drop_down,
                color: SilverTokens.greenBright, size: 28),
          ),
      ],
    );
  }
}

class ScanFrame extends StatelessWidget {
  const ScanFrame({super.key});

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: <Widget>[
        const Positioned(
            top: 10, left: 10, child: Corner(top: true, left: true)),
        const Positioned(
            top: 10, right: 10, child: Corner(top: true, left: false)),
        const Positioned(
            bottom: 10, left: 10, child: Corner(top: false, left: true)),
        const Positioned(
            bottom: 10, right: 10, child: Corner(top: false, left: false)),
        Positioned(
          left: 12,
          right: 12,
          top: 24,
          child: Container(
            height: 2,
            decoration: BoxDecoration(
              color: SilverTokens.greenBright,
              boxShadow: <BoxShadow>[
                BoxShadow(
                    color: SilverTokens.greenBright.withValues(alpha: 0.8),
                    blurRadius: 10)
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class Corner extends StatelessWidget {
  const Corner({required this.top, required this.left, super.key});

  final bool top;
  final bool left;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 26,
      height: 26,
      decoration: BoxDecoration(
        border: Border(
          top: top
              ? const BorderSide(color: SilverTokens.greenBright, width: 3)
              : BorderSide.none,
          bottom: !top
              ? const BorderSide(color: SilverTokens.greenBright, width: 3)
              : BorderSide.none,
          left: left
              ? const BorderSide(color: SilverTokens.greenBright, width: 3)
              : BorderSide.none,
          right: !left
              ? const BorderSide(color: SilverTokens.greenBright, width: 3)
              : BorderSide.none,
        ),
      ),
    );
  }
}

class StepperHeader extends StatelessWidget {
  const StepperHeader({required this.step, super.key});

  final int step;

  @override
  Widget build(BuildContext context) {
    final List<String> labels = <String>[
      'Chụp ảnh',
      'Thông tin',
      'Gắn nhãn',
      'Xác nhận'
    ];
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: labels.indexed
            .expand(
              (entry) => <Widget>[
                SizedBox(
                  width: 56,
                  child: Column(
                    children: <Widget>[
                      CircleAvatar(
                        radius: 15,
                        backgroundColor:
                            entry.$1 <= step ? SilverTokens.blue : Colors.white,
                        child: entry.$1 < step
                            ? const Icon(Icons.check,
                                size: 16, color: Colors.white)
                            : Text(
                                '${entry.$1 + 1}',
                                style: TextStyle(
                                  color: entry.$1 <= step
                                      ? Colors.white
                                      : SilverTokens.ink3,
                                  fontSize: 14,
                                  fontWeight: FontWeight.w900,
                                ),
                              ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        entry.$2,
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: entry.$1 == step
                              ? SilverTokens.blue
                              : SilverTokens.ink3,
                          fontSize: 11,
                          height: 1.1,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ],
                  ),
                ),
                if (entry.$1 < labels.length - 1)
                  Expanded(
                    child: Container(
                      height: 2.5,
                      margin: const EdgeInsets.only(top: 14),
                      decoration: BoxDecoration(
                        color: entry.$1 < step
                            ? SilverTokens.blue
                            : SilverTokens.blueTint2,
                        borderRadius: BorderRadius.circular(2),
                      ),
                    ),
                  ),
              ],
            )
            .toList(),
      ),
    );
  }
}

class InfoCard extends StatelessWidget {
  const InfoCard({
    required this.index,
    required this.title,
    required this.subtitle,
    this.tone = 'blue',
    super.key,
  });

  final String index;
  final String title;
  final String subtitle;
  final String tone;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
          color: toneTint(tone), borderRadius: BorderRadius.circular(16)),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            width: 30,
            height: 30,
            alignment: Alignment.center,
            decoration: BoxDecoration(
                color: toneColor(tone), borderRadius: BorderRadius.circular(9)),
            child: Text(index,
                style: const TextStyle(
                    color: Colors.white,
                    fontSize: 15,
                    fontWeight: FontWeight.w900)),
          ),
          const SizedBox(width: 13),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(title,
                    style: const TextStyle(
                        color: SilverTokens.ink,
                        fontSize: 17,
                        fontWeight: FontWeight.w900)),
                const SizedBox(height: 3),
                Text(subtitle,
                    style: const TextStyle(
                        color: SilverTokens.ink2,
                        fontSize: 14,
                        height: 1.35,
                        fontWeight: FontWeight.w700)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class TipBox extends StatelessWidget {
  const TipBox({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 13),
      decoration: BoxDecoration(
        color: SilverTokens.amberTint,
        borderRadius: BorderRadius.circular(14),
        border:
            Border.all(color: SilverTokens.amberLine.withValues(alpha: 0.4)),
      ),
      child: const Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(Icons.warning_amber_rounded,
              color: SilverTokens.amberLine, size: 20),
          SizedBox(width: 11),
          Expanded(
            child: Text(
              'Mẹo: Chụp toàn bộ mặt trước, thấy rõ cụm nút và tên/model nếu có',
              style: TextStyle(
                  color: Color(0xFF8A6A14),
                  fontSize: 14,
                  height: 1.35,
                  fontWeight: FontWeight.w700),
            ),
          ),
        ],
      ),
    );
  }
}

class InstructionCard extends StatelessWidget {
  const InstructionCard({
    required this.step,
    required this.data,
    required this.done,
    super.key,
  });

  final int step;
  final GuideStepData data;
  final bool done;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(17),
      decoration: BoxDecoration(
        color: done ? SilverTokens.greenTint : const Color(0xFFEAF4FB),
        borderRadius: BorderRadius.circular(16),
        border: Border(
            left: BorderSide(
                color: done ? SilverTokens.green : SilverTokens.blue,
                width: 4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Bước ${step + 1}: ${data.kind}',
            style: TextStyle(
              color: done ? SilverTokens.green : SilverTokens.blue,
              fontSize: 13.5,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 4),
          Row(
            children: <Widget>[
              if (done)
                const Padding(
                    padding: EdgeInsets.only(right: 9),
                    child:
                        Icon(Icons.check, color: SilverTokens.green, size: 26)),
              Expanded(
                child: Text(
                  data.title,
                  style: const TextStyle(
                      color: SilverTokens.ink,
                      fontSize: 24,
                      fontWeight: FontWeight.w900),
                ),
              ),
            ],
          ),
          const SizedBox(height: 5),
          Text(data.hint,
              style: const TextStyle(
                  color: SilverTokens.ink2,
                  fontSize: 15.5,
                  height: 1.35,
                  fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }
}

class StatBox extends StatelessWidget {
  const StatBox({
    required this.big,
    required this.small,
    required this.tone,
    super.key,
  });

  final String big;
  final String small;
  final String tone;

  @override
  Widget build(BuildContext context) {
    final Color color = tone == 'green' ? SilverTokens.green : SilverTokens.red;
    final Color bg =
        tone == 'green' ? SilverTokens.greenTint : SilverTokens.redSoft;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 16),
      decoration:
          BoxDecoration(color: bg, borderRadius: BorderRadius.circular(16)),
      child: Column(
        children: <Widget>[
          Text(big,
              style: TextStyle(
                  color: color,
                  fontSize: 30,
                  height: 1,
                  fontWeight: FontWeight.w900)),
          const SizedBox(height: 4),
          Text(small,
              style: TextStyle(
                  color: color, fontSize: 14, fontWeight: FontWeight.w900)),
        ],
      ),
    );
  }
}

class StatusPill extends StatelessWidget {
  const StatusPill({
    required this.label,
    required this.color,
    required this.bg,
    this.dot = true,
    super.key,
  });

  final String label;
  final Color color;
  final Color bg;
  final bool dot;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration:
          BoxDecoration(color: bg, borderRadius: BorderRadius.circular(999)),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 250),
        child: FittedBox(
          fit: BoxFit.scaleDown,
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              if (dot) ...<Widget>[
                CircleAvatar(backgroundColor: color, radius: 4.5),
                const SizedBox(width: 7),
              ],
              Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                    color: color, fontSize: 14, fontWeight: FontWeight.w900),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class FooterActions extends StatelessWidget {
  const FooterActions({
    required this.children,
    this.column = false,
    super.key,
  });

  final List<Widget> children;
  final bool column;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 10, 20, 30),
      child: column ? Column(children: children) : Row(children: children),
    );
  }
}

/// Shows the on-device ASR transcript on the voice screen so the user can see
/// exactly what was heard before asking for guidance.
class _TranscriptCard extends StatelessWidget {
  const _TranscriptCard({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.white.withValues(alpha: 0.18)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Row(
            children: <Widget>[
              Icon(Icons.hearing, color: Color(0xFFBFE0FF), size: 18),
              SizedBox(width: 6),
              Text(
                'Nghe được',
                style: TextStyle(
                  color: Color(0xFFBFE0FF),
                  fontSize: 13,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            text,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 19,
              fontWeight: FontWeight.w800,
              height: 1.25,
            ),
          ),
        ],
      ),
    );
  }
}

class PrimaryButton extends StatelessWidget {
  const PrimaryButton({
    required this.label,
    required this.onTap,
    this.icon,
    this.iconAfter,
    this.enabled = true,
    this.compact = false,
    super.key,
  });

  final String label;
  final VoidCallback onTap;
  final IconData? icon;
  final IconData? iconAfter;
  final bool enabled;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return PrototypeButton(
      label: label,
      icon: icon,
      iconAfter: iconAfter,
      enabled: enabled,
      compact: compact,
      gradient: const LinearGradient(
          colors: <Color>[SilverTokens.blueBright, SilverTokens.blueDeep]),
      color: Colors.white,
      onTap: onTap,
    );
  }
}

class GreenButton extends StatelessWidget {
  const GreenButton({
    required this.label,
    required this.icon,
    required this.onTap,
    this.enabled = true,
    super.key,
  });

  final String label;
  final IconData icon;
  final VoidCallback onTap;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    return PrototypeButton(
      label: label,
      icon: icon,
      gradient: const LinearGradient(
          colors: <Color>[SilverTokens.greenBright, SilverTokens.green]),
      color: Colors.white,
      enabled: enabled,
      onTap: onTap,
    );
  }
}

class NeutralButton extends StatelessWidget {
  const NeutralButton({
    required this.label,
    required this.onTap,
    this.icon,
    this.enabled = true,
    this.compact = false,
    super.key,
  });

  final String label;
  final IconData? icon;
  final VoidCallback onTap;
  final bool enabled;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return PrototypeButton(
      label: label,
      icon: icon,
      enabled: enabled,
      compact: compact,
      background: SilverTokens.surface,
      color: SilverTokens.ink2,
      onTap: onTap,
    );
  }
}

class SecondaryDashedButton extends StatelessWidget {
  const SecondaryDashedButton({
    required this.label,
    required this.icon,
    required this.onTap,
    super.key,
  });

  final String label;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return PrototypeButton(
      label: label,
      icon: icon,
      background: SilverTokens.surface,
      color: SilverTokens.blue,
      border: Border.all(color: SilverTokens.blueTint2, width: 1.5),
      onTap: onTap,
    );
  }
}

class SmallPrimaryButton extends StatelessWidget {
  const SmallPrimaryButton({
    required this.label,
    required this.icon,
    required this.onTap,
    super.key,
  });

  final String label;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return PrototypeButton(
      label: label,
      icon: icon,
      minHeight: 46,
      gradient: const LinearGradient(
          colors: <Color>[SilverTokens.blueBright, SilverTokens.blueDeep]),
      color: Colors.white,
      onTap: onTap,
    );
  }
}

class PrototypeButton extends StatelessWidget {
  const PrototypeButton({
    required this.label,
    required this.color,
    required this.onTap,
    this.icon,
    this.iconAfter,
    this.gradient,
    this.background,
    this.border,
    this.enabled = true,
    this.compact = false,
    this.minHeight = 54,
    super.key,
  });

  final String label;
  final IconData? icon;
  final IconData? iconAfter;
  final LinearGradient? gradient;
  final Color? background;
  final Border? border;
  final Color color;
  final VoidCallback onTap;
  final bool enabled;
  final bool compact;
  final double minHeight;

  @override
  Widget build(BuildContext context) {
    final Color effectiveColor =
        enabled ? color : color.withValues(alpha: 0.45);
    return Opacity(
      opacity: enabled ? 1 : 0.45,
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          onTap: enabled ? onTap : null,
          borderRadius: BorderRadius.circular(16),
          child: Container(
            constraints: BoxConstraints(minHeight: minHeight),
            padding: EdgeInsets.symmetric(horizontal: compact ? 6 : 16),
            decoration: BoxDecoration(
              color: background,
              gradient: gradient,
              border: border,
              borderRadius: BorderRadius.circular(16),
              boxShadow: gradient == null
                  ? const <BoxShadow>[
                      BoxShadow(
                          color: Color(0x10203456),
                          blurRadius: 10,
                          offset: Offset(0, 2)),
                    ]
                  : const <BoxShadow>[],
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                if (icon != null) ...<Widget>[
                  Icon(icon, color: effectiveColor, size: compact ? 18 : 20),
                  SizedBox(width: compact ? 5 : 9),
                ],
                Flexible(
                  child: Text(
                    label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: effectiveColor,
                      fontSize: compact ? 14 : 16.5,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
                if (iconAfter != null) ...<Widget>[
                  SizedBox(width: compact ? 5 : 9),
                  Icon(iconAfter,
                      color: effectiveColor, size: compact ? 18 : 20),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class PrototypeTabBar extends StatelessWidget {
  const PrototypeTabBar({
    required this.active,
    required this.onHome,
    required this.onDevices,
    super.key,
  });

  final String active;
  final VoidCallback onHome;
  final VoidCallback onDevices;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 30),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.92),
        border: const Border(top: BorderSide(color: Color(0x12203456))),
      ),
      child: Row(
        children: <Widget>[
          Expanded(
              child: TabItem(
                  label: 'Trang chủ',
                  icon: Icons.home_outlined,
                  active: active == 'home',
                  onTap: onHome)),
          Expanded(
              child: TabItem(
                  label: 'Thiết bị',
                  icon: Icons.grid_view,
                  active: active == 'devices',
                  onTap: onDevices)),
        ],
      ),
    );
  }
}

class TabItem extends StatelessWidget {
  const TabItem({
    required this.label,
    required this.icon,
    required this.active,
    required this.onTap,
    super.key,
  });

  final String label;
  final IconData icon;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final Color color = active ? SilverTokens.blue : SilverTokens.ink3;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(icon, color: color, size: 26),
            const SizedBox(height: 4),
            Text(label,
                style: TextStyle(
                    color: color, fontSize: 12.5, fontWeight: FontWeight.w900)),
          ],
        ),
      ),
    );
  }
}

class SettingsRow extends StatelessWidget {
  const SettingsRow({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.control,
    this.last = false,
    super.key,
  });

  final Widget icon;
  final String title;
  final String subtitle;
  final Widget control;
  final bool last;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 16),
      decoration: BoxDecoration(
        border: last
            ? null
            : const Border(bottom: BorderSide(color: Color(0x12203456))),
      ),
      child: Row(
        children: <Widget>[
          Container(
            width: 42,
            height: 42,
            alignment: Alignment.center,
            decoration: BoxDecoration(
                color: SilverTokens.blueTint,
                borderRadius: BorderRadius.circular(12)),
            child: icon,
          ),
          const SizedBox(width: 13),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(title,
                    style: const TextStyle(
                        color: SilverTokens.ink,
                        fontSize: 17,
                        fontWeight: FontWeight.w900)),
                const SizedBox(height: 2),
                Text(subtitle,
                    style: const TextStyle(
                        color: SilverTokens.ink2,
                        fontSize: 13.5,
                        fontWeight: FontWeight.w700)),
              ],
            ),
          ),
          const SizedBox(width: 10),
          control,
        ],
      ),
    );
  }
}

class SegmentedTextSize extends StatelessWidget {
  const SegmentedTextSize({
    required this.value,
    required this.onChange,
    super.key,
  });

  final int value;
  final ValueChanged<int> onChange;

  @override
  Widget build(BuildContext context) {
    final List<String> labels = <String>['Vừa', 'To', 'Rất to'];
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
          color: SilverTokens.surface2,
          borderRadius: BorderRadius.circular(12)),
      child: Row(
        children: labels.indexed
            .map(
              (entry) => GestureDetector(
                onTap: () => onChange(entry.$1),
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 9, vertical: 8),
                  decoration: BoxDecoration(
                    color: value == entry.$1
                        ? SilverTokens.blue
                        : Colors.transparent,
                    borderRadius: BorderRadius.circular(9),
                  ),
                  child: Text(
                    entry.$2,
                    style: TextStyle(
                      color:
                          value == entry.$1 ? Colors.white : SilverTokens.ink2,
                      fontSize: 13,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
              ),
            )
            .toList(),
      ),
    );
  }
}

class ToastBanner extends StatelessWidget {
  const ToastBanner({required this.text, super.key});

  final String text;

  @override
  Widget build(BuildContext context) {
    return ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 340),
      child: Container(
        margin: const EdgeInsets.only(bottom: 76),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 15),
        decoration: BoxDecoration(
          color: SilverTokens.ink,
          borderRadius: BorderRadius.circular(16),
          boxShadow: const <BoxShadow>[
            BoxShadow(
                color: Color(0x52000000),
                blurRadius: 34,
                offset: Offset(0, 14)),
          ],
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const Icon(Icons.check, color: SilverTokens.greenBright),
            const SizedBox(width: 11),
            Expanded(
              child: Text(
                text,
                maxLines: 4,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w900),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

Color toneColor(String tone) {
  return switch (tone) {
    'green' => SilverTokens.green,
    'orange' => SilverTokens.orange,
    _ => SilverTokens.blue,
  };
}

Color toneTint(String tone) {
  return switch (tone) {
    'green' => SilverTokens.greenTint,
    'orange' => SilverTokens.orangeTint,
    'red' => SilverTokens.redSoft,
    _ => SilverTokens.blueTint,
  };
}
