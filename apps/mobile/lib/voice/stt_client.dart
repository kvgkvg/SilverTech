import 'voice_input.dart';
import 'sherpa_recognizer_stub.dart'
    if (dart.library.io) 'sherpa_recognizer.dart';

abstract class SpeechToTextClient {
  bool get isRecording;

  Future<void> warmUp();

  Future<bool> startListening();

  Future<String> stopAndTranscribe();

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
    if (samples.isEmpty) return '';
    final recognizer = _recognizer ??= await SherpaRecognizer.instance();
    return recognizer.recognize(samples, sampleRate: VoiceCapture.sampleRate);
  }

  @override
  void dispose() {
    _capture.dispose();
    _recognizer?.dispose();
  }
}
