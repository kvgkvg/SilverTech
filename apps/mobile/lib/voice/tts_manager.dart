import 'dart:async';

import 'package:flutter/foundation.dart' show debugPrint;
import 'package:flutter_tts/flutter_tts.dart';

/// Vietnamese text-to-speech for reading guidance steps aloud.
///
/// Backed by the platform speech engine (browser `SpeechSynthesis` on web —
/// works on plain Chromium, unlike Web Speech STT). Slow, clear rate tuned for
/// elderly users. Missing a `vi-VN` voice degrades to the default voice.
class TtsManager {
  TtsManager() {
    _configure();
  }

  final FlutterTts _tts = FlutterTts();
  bool _ready = false;

  Future<void> _configure() async {
    try {
      await _tts.setLanguage('vi-VN');
      await _tts.setSpeechRate(0.45);
      await _tts.setVolume(1.0);
      await _tts.setPitch(1.0);
      _ready = true;
    } catch (e) {
      debugPrint('[TTS] configure failed: $e');
    }
  }

  /// Stops any current utterance and speaks [text]. No-op on empty input.
  Future<void> speak(String text) async {
    final String trimmed = text.trim();
    if (trimmed.isEmpty) return;
    try {
      if (!_ready) await _configure();
      await _tts.stop();
      await _tts.speak(trimmed);
    } catch (e) {
      debugPrint('[TTS] speak failed: $e');
    }
  }

  Future<void> stop() async {
    try {
      await _tts.stop();
    } catch (_) {}
  }

  void dispose() {
    unawaited(_tts.stop());
  }
}
