import 'dart:typed_data';

class SherpaRecognizer {
  SherpaRecognizer._();

  static Future<SherpaRecognizer> instance() async => SherpaRecognizer._();

  String recognize(Float32List samples, {int sampleRate = 16000}) {
    throw UnsupportedError('On-device Vietnamese ASR is not available on web.');
  }

  void dispose() {}
}
