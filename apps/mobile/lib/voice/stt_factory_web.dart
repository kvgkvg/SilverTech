import 'stt_client.dart';
import 'web_speech_client.dart';

/// On web (Chrome): browser-native Web Speech API (sherpa has no web build).
SpeechToTextClient createPlatformSpeechToText() => WebSpeechClient();
