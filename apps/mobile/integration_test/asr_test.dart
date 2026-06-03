import 'dart:typed_data';

import 'package:flutter/services.dart' show rootBundle;
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:silvertech_mobile/voice/sherpa_recognizer.dart';

/// Runs real sherpa-onnx ASR on bundled 16 kHz mono test wavs.
/// Execute on a device/emulator (native onnxruntime required):
///   flutter test integration_test/asr_test.dart -d <device>
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  test('transcribes Vietnamese test wav to non-empty text', () async {
    final recognizer = await SherpaRecognizer.instance();

    for (final name in <String>['assets/test/0.wav', 'assets/test/1.wav']) {
      final samples = await _loadWavAsFloat32(name);
      expect(samples.isNotEmpty, true, reason: '$name decoded to no samples');

      final text = recognizer.recognize(samples, sampleRate: 16000);
      // ignore: avoid_print
      print('ASR[$name] => "$text"');
      expect(text.trim().isNotEmpty, true, reason: '$name produced empty text');
    }
  });
}

/// Loads a 16-bit PCM mono WAV asset and returns float samples in [-1, 1].
Future<Float32List> _loadWavAsFloat32(String asset) async {
  final ByteData data = await rootBundle.load(asset);
  final bytes = data.buffer.asUint8List();

  // Locate the "data" sub-chunk rather than assuming a 44-byte header.
  int offset = 12; // skip RIFF + size + WAVE
  int dataStart = 44;
  int dataLen = bytes.length - 44;
  while (offset + 8 <= bytes.length) {
    final id = String.fromCharCodes(bytes.sublist(offset, offset + 4));
    final size = data.getUint32(offset + 4, Endian.little);
    if (id == 'data') {
      dataStart = offset + 8;
      dataLen = size;
      break;
    }
    offset += 8 + size + (size & 1);
  }

  final view = ByteData.sublistView(data, dataStart, dataStart + dataLen);
  final n = dataLen ~/ 2;
  final out = Float32List(n);
  for (int i = 0; i < n; i++) {
    out[i] = view.getInt16(i * 2, Endian.little) / 32768.0;
  }
  return out;
}
