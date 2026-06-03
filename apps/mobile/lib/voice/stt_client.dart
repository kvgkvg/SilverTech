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
    if (samples.isEmpty) return '';
    final recognizer = _recognizer ??= await SherpaRecognizer.instance();
    return recognizer.recognize(samples, sampleRate: VoiceCapture.sampleRate);
  }

  void dispose() {
    _capture.dispose();
    _recognizer?.dispose();
  }
}
