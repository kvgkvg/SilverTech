import 'stt_client.dart';

/// On mobile/desktop: on-device sherpa-onnx Vietnamese ASR.
SpeechToTextClient createPlatformSpeechToText() => STTClient();
