import 'package:audioplayers/audioplayers.dart';

import '../backend/silver_backend.dart';

/// Resolves the `audio_url` a guidance step carries into a playable url.
///
/// The backend returns a server-relative path (`/data/tts/<hash>.mp3`), so it
/// has to be joined onto the API base url before playback.
String? resolveAudioUrl(String baseUrl, String? audioUrl) {
  if (audioUrl == null || audioUrl.isEmpty) {
    return null;
  }
  if (Uri.parse(audioUrl).hasScheme) {
    return audioUrl;
  }
  final String base =
      baseUrl.endsWith('/') ? baseUrl.substring(0, baseUrl.length - 1) : baseUrl;
  final String path = audioUrl.startsWith('/') ? audioUrl : '/$audioUrl';
  return '$base$path';
}

/// Plays the Vietnamese audio the backend synthesised for a guidance step.
///
/// Playback uses server-side audio rather than an on-device engine because
/// `flutter_tts` has no Linux implementation, and the desktop/web demo targets
/// need one path that works on both.
class TTSManager {
  TTSManager({AudioPlayer? player, String? baseUrl})
      : _player = player ?? AudioPlayer(),
        _baseUrl = baseUrl ?? defaultSilverTechApiBaseUrl;

  final AudioPlayer _player;
  final String _baseUrl;

  /// Plays [audioUrl], restarting it if already playing. No-op when the step
  /// carries no audio, which happens when server-side synthesis failed.
  Future<void> speak(String? audioUrl) async {
    final String? url = resolveAudioUrl(_baseUrl, audioUrl);
    if (url == null) {
      return;
    }
    await _player.stop();
    await _player.play(UrlSource(url));
  }

  Future<void> stop() => _player.stop();

  void dispose() {
    _player.dispose();
  }
}
