import 'dart:async';
import 'dart:js_interop';
import 'dart:js_interop_unsafe';

import 'package:flutter/foundation.dart' show debugPrint;

import 'stt_client.dart';

/// Browser-native Vietnamese STT for web (Chrome) via the Web Speech API
/// (`webkitSpeechRecognition`). Online (Google), Chromium-only. Used in place
/// of the on-device sherpa model, which is FFI-native and has no web build.
class WebSpeechClient implements SpeechToTextClient {
  WebSpeechClient();

  _Recognition? _rec;
  bool _recording = false;
  String _finalText = '';
  Completer<String>? _done;

  @override
  bool get isRecording => _recording;

  @override
  Future<void> warmUp() async {}

  @override
  Future<bool> startListening() async {
    if (_recording) return true;
    if (!_supported) {
      debugPrint('[STT-web] webkitSpeechRecognition not available');
      return false;
    }
    final rec = _Recognition()
      ..lang = 'vi-VN'
      ..continuous = true
      ..interimResults = true;
    _finalText = '';

    rec.onresult = ((_ResultEvent e) {
      final results = e.results;
      final sb = StringBuffer();
      for (var i = 0; i < results.length; i++) {
        final r = results[i];
        if (r.isFinal) sb.write(r[0].transcript);
      }
      _finalText = sb.toString().trim();
    }).toJS;

    rec.onerror = ((_ErrorEvent e) {
      debugPrint('[STT-web] error: ${e.error}');
    }).toJS;

    rec.onend = (() {
      _recording = false;
      _done?.complete(_finalText);
      _done = null;
    }).toJS;

    try {
      rec.start();
    } catch (e) {
      debugPrint('[STT-web] start failed: $e');
      return false;
    }
    _rec = rec;
    _recording = true;
    return true;
  }

  @override
  Future<String> stopAndTranscribe() async {
    final rec = _rec;
    if (rec == null || !_recording) return '';
    final completer = Completer<String>();
    _done = completer;
    rec.stop();
    final text = await completer.future.timeout(
      const Duration(seconds: 5),
      onTimeout: () => _finalText,
    );
    debugPrint('[STT-web] recognized: "$text"');
    return text;
  }

  /// Web Speech API listens to the live mic only — it cannot decode a WAV file.
  @override
  Future<String> transcribeAsset(String assetKey) async {
    throw UnsupportedError(
      'Self-test mẫu WAV không hỗ trợ trên web (Web Speech API chỉ nghe mic).',
    );
  }

  @override
  void dispose() {
    _rec?.stop();
    _rec = null;
    _recording = false;
  }
}

bool get _supported =>
    globalContext.has('webkitSpeechRecognition') ||
    globalContext.has('SpeechRecognition');

@JS('webkitSpeechRecognition')
extension type _Recognition._(JSObject _) implements JSObject {
  external factory _Recognition();
  external set lang(String value);
  external set continuous(bool value);
  external set interimResults(bool value);
  external set onresult(JSFunction value);
  external set onerror(JSFunction value);
  external set onend(JSFunction value);
  external void start();
  external void stop();
}

extension type _ResultEvent._(JSObject _) implements JSObject {
  external _ResultList get results;
}

extension type _ResultList._(JSObject _) implements JSObject {
  external int get length;
  external _Result operator [](int index);
}

extension type _Result._(JSObject _) implements JSObject {
  external _Alternative operator [](int index);
  external bool get isFinal;
}

extension type _Alternative._(JSObject _) implements JSObject {
  external String get transcript;
}

extension type _ErrorEvent._(JSObject _) implements JSObject {
  external String get error;
}
