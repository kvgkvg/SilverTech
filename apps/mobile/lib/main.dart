import 'dart:async';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

void main() {
  runApp(const SilverTechApp());
}

class SilverTechApp extends StatelessWidget {
  const SilverTechApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SilverTech',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF0B6E4F)),
        scaffoldBackgroundColor: Colors.white,
        textTheme: const TextTheme(
          headlineMedium: TextStyle(fontSize: 30, fontWeight: FontWeight.w700),
          bodyLarge: TextStyle(fontSize: 24),
          labelLarge: TextStyle(fontSize: 22, fontWeight: FontWeight.w700),
        ),
      ),
      home: const CameraEntryScreen(),
    );
  }
}

class CameraEntryScreen extends StatelessWidget {
  const CameraEntryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('SilverTech')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            const Text(
              'Huong camera vao bang dieu khien.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 30, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 24),
            const Text(
              'Neu hinh anh chua ro, ung dung se yeu cau quet lai thay vi doan nut.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 24),
            ),
            const SizedBox(height: 32),
            SizedBox(
              height: 64,
              child: FilledButton(
                onPressed: () {
                  Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => const CameraScanScreen(),
                    ),
                  );
                },
                child: const Text('Mo camera'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class CameraScanScreen extends StatefulWidget {
  const CameraScanScreen({super.key});

  @override
  State<CameraScanScreen> createState() => _CameraScanScreenState();
}

class _CameraScanScreenState extends State<CameraScanScreen> {
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
    final colorScheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(title: const Text('Quet bang dieu khien')),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Expanded(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: const Color(0xFFF4F8F5),
                  border: Border.all(color: colorScheme.primary, width: 4),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: FutureBuilder<void>(
                    future: _cameraInitialization,
                    builder: (context, snapshot) {
                      if (snapshot.connectionState != ConnectionState.done) {
                        return const Center(
                          child: CircularProgressIndicator(),
                        );
                      }

                      if (snapshot.hasError || _cameraController == null) {
                        return const _CameraUnavailableView();
                      }

                      return Stack(
                        fit: StackFit.expand,
                        children: <Widget>[
                          FittedBox(
                            fit: BoxFit.cover,
                            child: SizedBox(
                              width:
                                  _cameraController!.value.previewSize?.height,
                              height:
                                  _cameraController!.value.previewSize?.width,
                              child: CameraPreview(_cameraController!),
                            ),
                          ),
                          const _CameraInstructionOverlay(),
                        ],
                      );
                    },
                  ),
                ),
              ),
            ),
            const SizedBox(height: 20),
            const Text(
              'Khi do tin cay thap, SilverTech se yeu cau quet lai va khong hien nut.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 22),
            ),
            const SizedBox(height: 20),
            SizedBox(
              height: 64,
              child: FilledButton(
                onPressed: () {
                  setState(() {
                    _cameraInitialization = _initializeCamera();
                  });
                },
                child: const Text('Quet lai'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CameraInstructionOverlay extends StatelessWidget {
  const _CameraInstructionOverlay();

  @override
  Widget build(BuildContext context) {
    return const Align(
      alignment: Alignment.topCenter,
      child: Padding(
        padding: EdgeInsets.all(16),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: Color(0xCC000000),
            borderRadius: BorderRadius.all(Radius.circular(8)),
          ),
          child: Padding(
            padding: EdgeInsets.all(12),
            child: Text(
              'Dat bang dieu khien vao khung hinh',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white,
                fontSize: 24,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _CameraUnavailableView extends StatelessWidget {
  const _CameraUnavailableView();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Padding(
        padding: EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Text(
              'Dat bang dieu khien vao khung hinh',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 30,
                fontWeight: FontWeight.w700,
              ),
            ),
            SizedBox(height: 16),
            Text(
              'Khong mo duoc camera. Hay kiem tra quyen camera hoac chay tren dien thoai/trinh duyet co camera.',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 22,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
