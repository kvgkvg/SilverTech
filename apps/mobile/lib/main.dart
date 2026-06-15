import 'dart:async';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

import 'backend/silver_backend.dart';
import 'guidance/guidance_client.dart';
import 'templates/template_repository_client.dart';
import 'vision/detection_controller.dart';
import 'vision/frame_source_factory.dart';
import 'vision/geometry.dart';
import 'voice/stt_client.dart';
import 'voice/stt_factory.dart';
import 'voice/tts_manager.dart';

void main() {
  runApp(const SilverTechApp());
}

class SilverTechApp extends StatelessWidget {
  const SilverTechApp({this.backend, this.speechToText, super.key});

  final SilverBackendGateway? backend;
  final SpeechToTextClient? speechToText;

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
  });

  final String id;
  final String kind;
  final String tone;
  final String name;
  final String short;
  final String model;
  final String last;
}

class GuideStepData {
  const GuideStepData({
    required this.kind,
    required this.buttonId,
    required this.title,
    required this.hint,
  });

  final String kind;
  final String buttonId;
  final String title;
  final String hint;
}

class RouteState {
  const RouteState(this.screen, {this.device});

  final String screen;
  final DemoDevice? device;
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
    super.key,
  });

  final SilverBackendGateway backend;
  final SpeechToTextClient? speechToText;

  @override
  State<SilverPrototypeShell> createState() => _SilverPrototypeShellState();
}

class _SilverPrototypeShellState extends State<SilverPrototypeShell> {
  List<DemoDevice> _devices = List<DemoDevice>.from(initialDevices);
  List<RouteState> _stack = const <RouteState>[RouteState('home')];
  String _tab = 'home';
  String? _toast;
  bool _recognitionBusy = false;
  bool _voiceBusy = false;
  double _recognitionMatchScore = 0;
  TemplateDetailDto? _selectedTemplate;
  DetectionController? _detection;
  List<ProjectedButton> _projectedButtons = const <ProjectedButton>[];
  List<GuideStepData> _currentGuideSteps = guideSteps;
  late final SpeechToTextClient _stt;
  Future<bool>? _startFuture;
  String _recognizedText = '';

  @override
  void initState() {
    super.initState();
    _stt = widget.speechToText ?? createPlatformSpeechToText();
    // Preload ASR model so first hold-to-talk is responsive.
    _stt.warmUp();
  }

  @override
  void dispose() {
    _detection?.stop();
    _stt.dispose();
    super.dispose();
  }

  RouteState get _current => _stack.last;

  void _nav(String target, {DemoDevice? device}) {
    final String fromScreen = _current.screen;
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
      _stack = <RouteState>[..._stack, RouteState(target, device: device)];
    });
    final String toScreen = _current.screen;
    // Stop any live detection loop the moment we leave the recognize screen so
    // no periodic Timer leaks (back button, proceeding to voice, etc.).
    if (fromScreen == 'recognize' && toScreen != 'recognize') {
      _stopLiveDetection();
    }
    // Entering the recognize screen kicks off the real detect loop.
    if (toScreen == 'recognize' && fromScreen != 'recognize') {
      _startLiveDetection();
    }
  }

  void _stopLiveDetection() {
    _detection?.stop();
    _detection = null;
  }

  Future<void> _startLiveDetection() async {
    setState(() {
      _recognitionBusy = true;
      _recognitionMatchScore = 0;
      _selectedTemplate = null;
      _projectedButtons = const <ProjectedButton>[];
    });
    try {
      final source = await createFrameSource();
      // We may have navigated away while the frame source was opening; abort so
      // no orphaned periodic Timer is created after leaving the recognize screen.
      if (!mounted || _current.screen != 'recognize') {
        await source.stop();
        return;
      }
      final controller = DetectionController(
        source: source,
        matcher: (frame) => widget.backend
            .match(frame, brand: 'Panasonic', applianceType: 'microwave'),
      );
      _detection = controller;
      controller.state.addListener(() => _onDetectionState(controller));
      await controller.start();
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _recognitionBusy = false;
        _toast = 'Không mở được camera.';
      });
    }
  }

  void _onDetectionState(DetectionController controller) {
    if (!mounted) return;
    final s = controller.state.value;
    switch (s.phase) {
      case DetectionPhase.scanning:
        setState(() {
          _recognitionMatchScore = s.matchScore ?? 0;
          _projectedButtons = s.polygons;
        });
        break;
      case DetectionPhase.rejected:
        setState(() {
          _recognitionMatchScore = 0;
          _projectedButtons = const <ProjectedButton>[];
        });
        break;
      case DetectionPhase.matched:
        _onTemplateMatched(s);
        break;
      case DetectionPhase.idle:
        break;
    }
  }

  Future<void> _onTemplateMatched(DetectionState s) async {
    final templateId = s.templateId;
    if (templateId == null) return;
    final controller = _detection;
    if (controller == null) return; // already handled by a prior matched tick
    _detection = null; // claim synchronously so re-entry returns above
    // Self-stop the loop on lock-on (also frees the periodic Timer).
    await controller.stop();
    try {
      final template = await widget.backend.fetchTemplate(templateId);
      if (!mounted) return;
      setState(() {
        _selectedTemplate = template;
        _recognitionMatchScore = s.matchScore ?? 0;
        _projectedButtons = s.polygons;
        _recognitionBusy = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _recognitionBusy = false;
        _toast = 'Không tải được mẫu thiết bị.';
      });
    }
  }

  /// User confirmed the locked-on template. Proceed to the voice step using the
  /// matched [_selectedTemplate] (does NOT call recognizeDefault anymore).
  void _useRecognitionResult() {
    final TemplateDetailDto? template = _selectedTemplate;
    if (template == null) {
      setState(() => _toast = 'Chưa nhận diện được thiết bị. Vui lòng giữ máy ổn định.');
      return;
    }
    final DemoDevice device = _deviceFromTemplate(template);
    _stopLiveDetection();
    setState(() {
      _recognitionBusy = false;
      _stack = <RouteState>[..._stack, RouteState('voice', device: device)];
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
    setState(() {
      _devices = <DemoDevice>[newDevice, ..._devices];
      _tab = 'devices';
      _stack = const <RouteState>[RouteState('devices')];
      _toast = 'Đã lưu "$name"';
    });
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

  Future<void> _askBackendGuidance(DemoDevice device,
      {required String query}) async {
    final String? templateId = _selectedTemplate?.id;
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
          onUseResult: _useRecognitionResult,
          busy: _recognitionBusy,
          matchScore: _recognitionMatchScore,
          template: _selectedTemplate,
          projectedButtons: _projectedButtons,
        ),
      'voice' => VoiceScreen(
          device: _current.device ?? acDevice,
          template: _selectedTemplate,
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
          steps: _currentGuideSteps,
          onNavigate: _nav,
        ),
      'add' => AddDeviceScreen(
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
        ...devices.take(2).map(
              (DemoDevice device) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: DeviceRow(
                  device: device,
                  onTap: () => onNavigate('voice', device: device),
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

class RecognizeScreen extends StatelessWidget {
  const RecognizeScreen({
    required this.onNavigate,
    required this.onUseResult,
    required this.busy,
    required this.matchScore,
    this.template,
    this.projectedButtons = const <ProjectedButton>[],
    super.key,
  });

  final void Function(String target, {DemoDevice? device}) onNavigate;
  final void Function() onUseResult;
  final bool busy;
  final double matchScore;
  final TemplateDetailDto? template;
  final List<ProjectedButton> projectedButtons;

  String _matchedDeviceName(TemplateDetailDto t) {
    switch (t.applianceType) {
      case 'air_conditioner':
        return 'Điều hòa ${t.brand}';
      case 'microwave':
        return 'Lò vi sóng ${t.brand}';
      default:
        return '${t.brand} ${t.applianceType}';
    }
  }

  @override
  Widget build(BuildContext context) {
    final TemplateDetailDto? matched = template;
    return Column(
      children: <Widget>[
        AppHeader(
            title: 'Nhận diện thiết bị', onBack: () => onNavigate('back')),
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 10),
            children: <Widget>[
              CameraCard(scanning: matched == null, polygons: projectedButtons),
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
              if (matched != null) ...<Widget>[
                Text(
                  _matchedDeviceName(matched),
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: SilverTokens.ink,
                    fontSize: 21,
                    height: 1.16,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  '${matched.buttons.length} nút',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: SilverTokens.ink2,
                    fontSize: 16,
                    height: 1.35,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ] else ...<Widget>[
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
              ],
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
                label: busy ? 'Đang lấy mẫu...' : 'Dùng kết quả này',
                icon: Icons.check,
                enabled: !busy,
                onTap: onUseResult,
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
    required this.steps,
    required this.onNavigate,
    super.key,
  });

  final DemoDevice device;
  final TemplateDetailDto? template;
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

  void _speakCurrent() {
    final GuideStepData data = widget.steps[step];
    _tts.speak('${data.title}. ${data.hint}');
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

class AddDeviceScreen extends StatefulWidget {
  const AddDeviceScreen({
    required this.onNavigate,
    required this.onSave,
    super.key,
  });

  final void Function(String target, {DemoDevice? device}) onNavigate;
  final void Function(String name) onSave;

  @override
  State<AddDeviceScreen> createState() => _AddDeviceScreenState();
}

class _AddDeviceScreenState extends State<AddDeviceScreen> {
  int step = 0;
  bool captured = false;
  String name = 'Điều hòa phòng khách';
  List<String> labels = <String>[
    'Nguồn',
    'Nhiệt độ +',
    'Nhiệt độ -',
    'Chế độ',
    'Quạt',
    'Hẹn giờ'
  ];

  void _next() => setState(() => step += 1);
  void _prev() => setState(() => step -= 1);

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
              if (step == 0)
                PhotoStep(
                    captured: captured,
                    onCapture: () => setState(() => captured = true)),
              if (step == 1) const DetectStep(),
              if (step == 2)
                LabelStep(
                    labels: labels,
                    onChanged: (List<String> next) =>
                        setState(() => labels = next)),
              if (step == 3)
                ConfirmStep(
                    name: name,
                    count: labels.length,
                    onChanged: (String next) => setState(() => name = next)),
            ],
          ),
        ),
        FooterActions(
          column: step == 0 || step == 3,
          children: <Widget>[
            if (step == 0) ...<Widget>[
              NeutralButton(
                  label: 'Ảnh chưa rõ? Chụp lại',
                  onTap: () => setState(() => captured = false)),
              const SizedBox(height: 10),
              PrimaryButton(
                  label: 'Tiếp theo',
                  iconAfter: Icons.arrow_forward,
                  enabled: captured,
                  onTap: _next),
            ],
            if (step == 1 || step == 2) ...<Widget>[
              Expanded(
                flex: 5,
                child: NeutralButton(
                    label: 'Bước trước', icon: Icons.arrow_back, onTap: _prev),
              ),
              const SizedBox(width: 10),
              Expanded(
                flex: 6,
                child: PrimaryButton(
                    label: 'Tiếp theo',
                    iconAfter: Icons.arrow_forward,
                    onTap: _next),
              ),
            ],
            if (step == 3) ...<Widget>[
              GreenButton(
                  label: 'Lưu thiết bị',
                  icon: Icons.check,
                  onTap: () => widget.onSave(name)),
              const SizedBox(height: 10),
              NeutralButton(label: 'Quay lại chỉnh sửa', onTap: _prev),
            ],
          ],
        ),
      ],
    );
  }
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
  const CameraCard({
    required this.scanning,
    this.polygons = const <ProjectedButton>[],
    super.key,
  });

  final bool scanning;

  /// Projected button polygons (in template image pixel space) from the live
  /// detection loop. Drawn as a best-effort overlay over the camera preview.
  final List<ProjectedButton> polygons;

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
                    polygons: widget.polygons,
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
    this.polygons = const <ProjectedButton>[],
    super.key,
  });

  final CameraController controller;
  final bool scanning;
  final double height;
  final List<ProjectedButton> polygons;

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
            if (polygons.isNotEmpty)
              Positioned.fill(
                child: CustomPaint(
                  painter: ButtonPolygonPainter(polygons: polygons),
                ),
              ),
            if (scanning) const ScanFrame(),
          ],
        ),
      ),
    );
  }
}

/// Best-effort overlay that draws the projected button polygons onto the live
/// preview. Polygon coordinates arrive in template-image pixel space; we fit
/// their shared bounding box into the preview rect so the boxes land roughly
/// where the buttons are without needing the source image's exact dimensions.
class ButtonPolygonPainter extends CustomPainter {
  ButtonPolygonPainter({required this.polygons});

  final List<ProjectedButton> polygons;

  @override
  void paint(Canvas canvas, Size size) {
    if (polygons.isEmpty) return;
    double minX = double.infinity;
    double minY = double.infinity;
    double maxX = double.negativeInfinity;
    double maxY = double.negativeInfinity;
    for (final ProjectedButton b in polygons) {
      for (final Point2 p in b.polygon) {
        if (p.x < minX) minX = p.x;
        if (p.y < minY) minY = p.y;
        if (p.x > maxX) maxX = p.x;
        if (p.y > maxY) maxY = p.y;
      }
    }
    final double spanX = (maxX - minX).abs() < 1e-6 ? 1 : maxX - minX;
    final double spanY = (maxY - minY).abs() < 1e-6 ? 1 : maxY - minY;
    // Inset the fitted box a little so polygons sit inside the preview frame.
    const double pad = 16;
    final double w = size.width - pad * 2;
    final double h = size.height - pad * 2;

    final Paint stroke = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3
      ..color = SilverTokens.green;
    final Paint fill = Paint()
      ..style = PaintingStyle.fill
      ..color = SilverTokens.green.withValues(alpha: 0.18);

    for (final ProjectedButton b in polygons) {
      if (b.polygon.isEmpty) continue;
      final Path path = Path();
      for (int i = 0; i < b.polygon.length; i++) {
        final Point2 p = b.polygon[i];
        final double dx = pad + ((p.x - minX) / spanX) * w;
        final double dy = pad + ((p.y - minY) / spanY) * h;
        if (i == 0) {
          path.moveTo(dx, dy);
        } else {
          path.lineTo(dx, dy);
        }
      }
      path.close();
      canvas.drawPath(path, fill);
      canvas.drawPath(path, stroke);
    }
  }

  @override
  bool shouldRepaint(covariant ButtonPolygonPainter oldDelegate) =>
      !identical(oldDelegate.polygons, polygons);
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

class TemplateDataPanel extends StatelessWidget {
  const TemplateDataPanel({
    required this.template,
    this.activeButtonId,
    super.key,
  });

  final TemplateDetailDto template;
  final String? activeButtonId;

  @override
  Widget build(BuildContext context) {
    final List<TemplateButtonDto> buttons = template.buttons;
    final Size imageSize = _templateImageSize(template);
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
      'Nhận diện',
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

class PhotoStep extends StatelessWidget {
  const PhotoStep({required this.captured, required this.onCapture, super.key});

  final bool captured;
  final VoidCallback onCapture;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: <Widget>[
        const InfoCard(
            index: '1',
            title: 'Chụp ảnh mặt trước thiết bị',
            subtitle: 'Đảm bảo đủ ánh sáng, thấy rõ toàn bộ nút bấm'),
        const SizedBox(height: 16),
        GestureDetector(
          onTap: onCapture,
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 34),
            decoration: BoxDecoration(
              color: captured ? SilverTokens.greenTint : SilverTokens.surface2,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(
                color: captured ? SilverTokens.green : const Color(0xFFC3D4E2),
                width: 2,
                style: captured ? BorderStyle.solid : BorderStyle.solid,
              ),
            ),
            child: Column(
              children: <Widget>[
                Container(
                  width: 60,
                  height: 60,
                  decoration: BoxDecoration(
                    color: captured ? SilverTokens.green : SilverTokens.surface,
                    borderRadius: BorderRadius.circular(18),
                  ),
                  child: Icon(captured ? Icons.check : Icons.photo_camera,
                      color: captured ? Colors.white : SilverTokens.ink2,
                      size: 30),
                ),
                const SizedBox(height: 10),
                Text(
                  captured ? 'Đã chụp ảnh' : 'Chạm để chụp ảnh',
                  style: const TextStyle(
                      color: SilverTokens.ink,
                      fontSize: 18,
                      fontWeight: FontWeight.w900),
                ),
                const SizedBox(height: 4),
                Text(
                  captured
                      ? 'Chạm lại để chụp ảnh khác'
                      : 'hoặc chọn từ thư viện',
                  style: const TextStyle(
                      color: SilverTokens.ink2,
                      fontSize: 14,
                      fontWeight: FontWeight.w700),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        const TipBox(),
      ],
    );
  }
}

class DetectStep extends StatelessWidget {
  const DetectStep({super.key});

  @override
  Widget build(BuildContext context) {
    return const Column(
      children: <Widget>[
        InfoCard(
            index: '2',
            title: 'Hệ thống đang nhận diện',
            subtitle: 'Đã tìm thấy các nút bấm trên ảnh của ông/bà'),
        SizedBox(height: 16),
        CameraCard(scanning: true),
        SizedBox(height: 16),
        Row(
          children: <Widget>[
            Expanded(
                child: StatBox(big: '1', small: 'thiết bị', tone: 'green')),
            SizedBox(width: 12),
            Expanded(child: StatBox(big: '6', small: 'nút bấm', tone: 'red')),
          ],
        ),
      ],
    );
  }
}

class LabelStep extends StatelessWidget {
  const LabelStep({
    required this.labels,
    required this.onChanged,
    super.key,
  });

  final List<String> labels;
  final void Function(List<String> labels) onChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: <Widget>[
        const InfoCard(
            index: '3',
            title: 'Kiểm tra tên các nút',
            subtitle: 'Chạm để sửa nếu tên nút chưa đúng'),
        const SizedBox(height: 16),
        ...labels.indexed.map(
          (entry) => Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: SilverCard(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              child: Row(
                children: <Widget>[
                  CircleAvatar(
                    radius: 15,
                    backgroundColor: SilverTokens.redSoft,
                    child: Text('${entry.$1 + 1}',
                        style: const TextStyle(
                            color: SilverTokens.red,
                            fontSize: 14,
                            fontWeight: FontWeight.w900)),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextFormField(
                      initialValue: entry.$2,
                      onChanged: (String value) {
                        final List<String> next = <String>[...labels];
                        next[entry.$1] = value;
                        onChanged(next);
                      },
                      style: const TextStyle(
                          color: SilverTokens.ink,
                          fontSize: 17,
                          fontWeight: FontWeight.w900),
                      decoration: const InputDecoration(
                          border: InputBorder.none, isDense: true),
                    ),
                  ),
                  const Icon(Icons.check, color: SilverTokens.ink3),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class ConfirmStep extends StatelessWidget {
  const ConfirmStep({
    required this.name,
    required this.count,
    required this.onChanged,
    super.key,
  });

  final String name;
  final int count;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: <Widget>[
        const InfoCard(
            index: '4',
            title: 'Xác nhận và lưu',
            subtitle: 'Đặt tên dễ nhớ cho thiết bị này',
            tone: 'green'),
        const SizedBox(height: 16),
        SilverCard(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const Text('TÊN THIẾT BỊ',
                  style: TextStyle(
                      color: SilverTokens.ink2,
                      fontSize: 13.5,
                      fontWeight: FontWeight.w900)),
              const SizedBox(height: 7),
              TextFormField(
                initialValue: name,
                onChanged: onChanged,
                style: const TextStyle(
                    color: SilverTokens.ink,
                    fontSize: 18,
                    fontWeight: FontWeight.w900),
                decoration: InputDecoration(
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(13),
                    borderSide: const BorderSide(
                        color: SilverTokens.blueTint2, width: 2),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(13),
                    borderSide:
                        const BorderSide(color: SilverTokens.blue, width: 2),
                  ),
                ),
              ),
              const SizedBox(height: 14),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 15, vertical: 13),
                decoration: BoxDecoration(
                    color: SilverTokens.greenTint,
                    borderRadius: BorderRadius.circular(13)),
                child: Row(
                  children: <Widget>[
                    const Icon(Icons.check,
                        color: SilverTokens.green, size: 24),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        '$count nút đã gắn nhãn xong',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                            color: SilverTokens.ink,
                            fontSize: 16,
                            fontWeight: FontWeight.w900),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
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
          children: <Widget>[
            const Icon(Icons.check, color: SilverTokens.greenBright),
            const SizedBox(width: 11),
            Expanded(
              child: Text(
                text,
                maxLines: 1,
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
