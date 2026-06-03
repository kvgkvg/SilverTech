import 'dart:async';
import 'dart:typed_data';

import 'package:record/record.dart';

class VoiceInputState {
  const VoiceInputState({required this.isRecording});
  final bool isRecording;
}

/// Captures mic audio as 16 kHz mono PCM and converts to float samples
/// suitable for [SherpaRecognizer]. Press-and-hold model: [start] on press,
/// [stop] on release returns the buffered waveform.
class VoiceCapture {
  static const int sampleRate = 16000;

  final AudioRecorder _recorder = AudioRecorder();
  final BytesBuilder _buffer = BytesBuilder(copy: false);
  StreamSubscription<Uint8List>? _sub;
  bool _recording = false;

  bool get isRecording => _recording;

  /// Starts streaming capture. Returns false if mic permission denied.
  Future<bool> start() async {
    if (_recording) return true;
    if (!await _recorder.hasPermission()) return false;
    _buffer.clear();
    final Stream<Uint8List> stream = await _recorder.startStream(
      const RecordConfig(
        encoder: AudioEncoder.pcm16bits,
        sampleRate: sampleRate,
        numChannels: 1,
      ),
    );
    _sub = stream.listen(_buffer.add);
    _recording = true;
    return true;
  }

  /// Stops capture and returns the recorded waveform as float32 in [-1, 1].
  Future<Float32List> stop() async {
    if (!_recording) return Float32List(0);
    await _recorder.stop();
    await _sub?.cancel();
    _sub = null;
    _recording = false;
    return _pcm16ToFloat32(_buffer.toBytes());
  }

  static Float32List _pcm16ToFloat32(Uint8List bytes) {
    final int n = bytes.length ~/ 2;
    final Float32List out = Float32List(n);
    final ByteData view = ByteData.sublistView(bytes);
    for (int i = 0; i < n; i++) {
      out[i] = view.getInt16(i * 2, Endian.little) / 32768.0;
    }
    return out;
  }

  void dispose() {
    _sub?.cancel();
    _recorder.dispose();
  }
}
