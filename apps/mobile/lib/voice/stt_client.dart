import 'package:flutter/foundation.dart' show debugPrint;

import 'voice_input.dart';
import 'sherpa_recognizer_stub.dart'
    if (dart.library.io) 'sherpa_recognizer.dart';

abstract class SpeechToTextClient {
  bool get isRecording;

  Future<void> warmUp();

  Future<bool> startListening();

  Future<String> stopAndTranscribe();

  /// Decodes a bundled WAV asset (mic-independent self-test).
  Future<String> transcribeAsset(String assetKey);

  void dispose();
}

/// On-device speech-to-text: mic capture (press/release) + sherpa-onnx
/// Vietnamese transducer. Replaces the former server `/api/stt` mock.
class STTClient implements SpeechToTextClient {
  STTClient();

  final VoiceCapture _capture = VoiceCapture();
  SherpaRecognizer? _recognizer;

  @override
  bool get isRecording => _capture.isRecording;

  /// Preloads the ASR model so the first transcription is not slow.
  @override
  Future<void> warmUp() async {
    _recognizer ??= await SherpaRecognizer.instance();
  }

  /// Begins listening. Returns false if mic permission denied.
  @override
  Future<bool> startListening() => _capture.start();

  /// Stops listening and returns the recognized Vietnamese text ('' if none).
  @override
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
  /// and returns the recognized text. Verifies the model → UI path even when
  /// the mic is silent. Throws [UnsupportedError] on web.
  @override
  Future<String> transcribeAsset(String assetKey) async {
    final recognizer = _recognizer ??= await SherpaRecognizer.instance();
    return recognizer.transcribeAsset(assetKey);
  }

  @override
  void dispose() {
    _capture.dispose();
    _recognizer?.dispose();
  }
}
