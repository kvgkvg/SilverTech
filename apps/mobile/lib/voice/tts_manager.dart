import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;

import '../backend/api_http_client.dart';
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
/// `flutter_tts` has no Linux implementation, and the desktop, Chrome and
/// Android demo targets need one path that works on all three.
class TtsManager {
  TtsManager({AudioPlayer? player, String? baseUrl, http.Client? httpClient})
      : _player = player ?? AudioPlayer(),
        _baseUrl = baseUrl ?? defaultSilverTechApiBaseUrl,
        _httpClient = httpClient ?? ApiHttpClient();

  final AudioPlayer _player;
  final String _baseUrl;
  final http.Client _httpClient;

  /// Plays [audioUrl], restarting it if already playing. No-op when the step
  /// carries no audio, which happens when server-side synthesis failed.
  Future<void> speak(String? audioUrl) async {
    final String? url = resolveAudioUrl(_baseUrl, audioUrl);
    if (url == null) {
      return;
    }
    await _player.stop();
    await _player.play(await _sourceFor(url));
  }

  /// On web an `UrlSource` becomes an `<audio src>` the browser fetches on its
  /// own, so it cannot carry the header that gets a response past ngrok's
  /// browser-warning page. Fetching the mp3 here keeps the header, and
  /// `audioplayers_web` replays the bytes as a data uri.
  ///
  /// Native stays on `UrlSource`: its `audioplayers_linux` backend implements
  /// only `setSourceUrl`, and a Dart VM user-agent never trips the warning.
  Future<Source> _sourceFor(String url) async {
    if (!kIsWeb) {
      return UrlSource(url);
    }
    final http.Response response = await _httpClient.get(Uri.parse(url));
    if (response.statusCode != 200) {
      throw TtsFetchException(url, response.statusCode);
    }
    return BytesSource(response.bodyBytes, mimeType: 'audio/mpeg');
  }

  Future<void> stop() => _player.stop();

  void dispose() {
    _player.dispose();
    _httpClient.close();
  }
}

class TtsFetchException implements Exception {
  const TtsFetchException(this.url, this.statusCode);

  final String url;
  final int statusCode;

  @override
  String toString() => 'TtsFetchException($url, status: $statusCode)';
}
