import 'dart:io';

import 'package:flutter/foundation.dart' show debugPrint;
import 'package:flutter/services.dart' show rootBundle;
import 'package:path_provider/path_provider.dart';
import 'package:sherpa_onnx/sherpa_onnx.dart' as sherpa;

import 'voice_input.dart';
import 'sherpa_recognizer.dart';

/// On-device speech-to-text: mic capture (press/release) + sherpa-onnx
/// Vietnamese transducer. Replaces the former server `/api/stt` mock.
class STTClient {
  STTClient();

  final VoiceCapture _capture = VoiceCapture();
  SherpaRecognizer? _recognizer;

  bool get isRecording => _capture.isRecording;

  /// Preloads the ASR model so the first transcription is not slow.
  Future<void> warmUp() async {
    _recognizer ??= await SherpaRecognizer.instance();
  }

  /// Begins listening. Returns false if mic permission denied.
  Future<bool> startListening() => _capture.start();

  /// Stops listening and returns the recognized Vietnamese text ('' if none).
  Future<String> stopAndTranscribe() async {
    final samples = await _capture.stop();
    final double seconds = samples.length / VoiceCapture.sampleRate;
    debugPrint('[STT] captured ${samples.length} samples '
        '(${seconds.toStringAsFixed(2)}s)');
    if (samples.isEmpty) return '';
    final recognizer = _recognizer ??= await SherpaRecognizer.instance();
    final String text =
        recognizer.recognize(samples, sampleRate: VoiceCapture.sampleRate);
    debugPrint('[STT] decoded text: "$text"');
    return text;
  }

  /// Mic-independent proof that the model works: decodes a bundled WAV asset
  /// (16 kHz mono PCM) and returns the recognized text. Use to verify the
  /// model → UI path even when the emulator mic is silent.
  Future<String> transcribeAsset(String assetKey) async {
    final recognizer = _recognizer ??= await SherpaRecognizer.instance();
    final data = await rootBundle.load(assetKey);
    final Directory tmp = await getTemporaryDirectory();
    final File file = File('${tmp.path}/${assetKey.split('/').last}');
    await file.writeAsBytes(
      data.buffer.asUint8List(data.offsetInBytes, data.lengthInBytes),
      flush: true,
    );
    final sherpa.WaveData wave = sherpa.readWave(file.path);
    debugPrint('[STT] wav ${wave.samples.length} samples sr=${wave.sampleRate}');
    if (wave.samples.isEmpty) return '';
    final String text =
        recognizer.recognize(wave.samples, sampleRate: wave.sampleRate);
    debugPrint('[STT] wav decoded: "$text"');
    return text;
  }

  void dispose() {
    _capture.dispose();
    _recognizer?.dispose();
  }
}
