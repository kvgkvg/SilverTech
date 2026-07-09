import 'package:flutter_test/flutter_test.dart';
import 'package:silvertech_mobile/voice/tts_manager.dart';

void main() {
  group('resolveAudioUrl', () {
    test('joins a server-relative path onto the API base url', () {
      expect(
        resolveAudioUrl('http://127.0.0.1:8000', '/data/tts/abc.mp3'),
        'http://127.0.0.1:8000/data/tts/abc.mp3',
      );
    });

    test('does not double the slash when the base url has a trailing one', () {
      expect(
        resolveAudioUrl('http://127.0.0.1:8000/', '/data/tts/abc.mp3'),
        'http://127.0.0.1:8000/data/tts/abc.mp3',
      );
    });

    test('joins a relative path that has no leading slash', () {
      expect(
        resolveAudioUrl('http://127.0.0.1:8000', 'data/tts/abc.mp3'),
        'http://127.0.0.1:8000/data/tts/abc.mp3',
      );
    });

    test('leaves an absolute url untouched', () {
      expect(
        resolveAudioUrl('http://127.0.0.1:8000', 'https://cdn.example/a.mp3'),
        'https://cdn.example/a.mp3',
      );
    });

    test('returns null when the step carries no audio', () {
      expect(resolveAudioUrl('http://127.0.0.1:8000', null), isNull);
      expect(resolveAudioUrl('http://127.0.0.1:8000', ''), isNull);
    });
  });
}
