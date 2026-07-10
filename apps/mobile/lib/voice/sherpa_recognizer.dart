import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/foundation.dart' show debugPrint;
import 'package:flutter/services.dart' show rootBundle;
import 'package:path_provider/path_provider.dart';
import 'package:sherpa_onnx/sherpa_onnx.dart' as sherpa;

/// On-device Vietnamese ASR backed by sherpa-onnx + the
/// `sherpa-onnx-zipformer-vi-30M-int8-2026-02-09` transducer model.
///
/// Offline, no network. Model files ship as Flutter assets under
/// `assets/models/asr/` and are copied to a writable dir on first run
/// because sherpa-onnx needs real filesystem paths (not asset keys).
class SherpaRecognizer {
  SherpaRecognizer._(this._recognizer);

  final sherpa.OfflineRecognizer _recognizer;
  static SherpaRecognizer? _instance;

  static const String _assetDir = 'assets/models/asr';
  static const List<String> _files = <String>[
    'encoder.int8.onnx',
    'decoder.onnx',
    'joiner.int8.onnx',
    'tokens.txt',
  ];

  /// Lazily initializes (model load is heavy — call once, e.g. at startup).
  /// Lazily initializes and returns the singleton instance of the offline ASR recognizer.
  ///
  /// Extracts the model files from assets onto disk on first run and loads the ONNX runtime
  /// configurations for offline Vietnamese speech-to-text inference.
  static Future<SherpaRecognizer> instance() async {
    final existing = _instance;
    if (existing != null) return existing;

    sherpa.initBindings();
    final String dir = await _copyAssetsToDisk();

    final modelConfig = sherpa.OfflineModelConfig(
      transducer: sherpa.OfflineTransducerModelConfig(
        encoder: '$dir/encoder.int8.onnx',
        decoder: '$dir/decoder.onnx',
        joiner: '$dir/joiner.int8.onnx',
      ),
      tokens: '$dir/tokens.txt',
      modelType: 'transducer',
      numThreads: 2,
      debug: false,
    );
    final config = sherpa.OfflineRecognizerConfig(model: modelConfig);
    final created = SherpaRecognizer._(sherpa.OfflineRecognizer(config));
    _instance = created;
    return created;
  }

  /// Transcribes 16 kHz mono float samples in [-1.0, 1.0]. Returns trimmed text.
  String recognize(Float32List samples, {int sampleRate = 16000}) {
    final stream = _recognizer.createStream();
    stream.acceptWaveform(samples: samples, sampleRate: sampleRate);
    _recognizer.decode(stream);
    final String text = _recognizer.getResult(stream).text;
    stream.free();
    return text.trim();
  }

  /// Mic-independent proof that the model works: decodes a bundled WAV asset
  /// (16 kHz mono PCM) and returns the recognized text. Use to verify the
  /// model → UI path even when the mic is silent.
  Future<String> transcribeAsset(String assetKey) async {
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
    final String text = recognize(wave.samples, sampleRate: wave.sampleRate);
    debugPrint('[STT] wav decoded: "$text"');
    return text;
  }

  void dispose() {
    _recognizer.free();
    _instance = null;
  }

  /// Bump when the bundled model files change so stale on-disk copies from a
  /// previous install are wiped and re-copied (size alone is unreliable —
  /// a wrong-model file can share byte length with the correct one).
  static const String _modelVersion = 'vi-30M-int8-2026-02-09';

  static Future<String> _copyAssetsToDisk() async {
    final Directory docs = await getApplicationDocumentsDirectory();
    final Directory dir = Directory('${docs.path}/asr_model');
    final File marker = File('${dir.path}/.model_version');

    final bool current =
        marker.existsSync() && marker.readAsStringSync() == _modelVersion;
    if (!current && dir.existsSync()) {
      dir.deleteSync(recursive: true); // drop stale/wrong-model files
    }
    if (!dir.existsSync()) {
      dir.createSync(recursive: true);
    }

    for (final String name in _files) {
      final File dest = File('${dir.path}/$name');
      if (current && dest.existsSync()) continue;
      final ByteData data = await rootBundle.load('$_assetDir/$name');
      await dest.writeAsBytes(
        data.buffer.asUint8List(data.offsetInBytes, data.lengthInBytes),
        flush: true,
      );
    }
    marker.writeAsStringSync(_modelVersion);
    return dir.path;
  }
}
