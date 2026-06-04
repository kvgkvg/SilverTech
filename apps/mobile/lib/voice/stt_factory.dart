// Returns the platform speech-to-text implementation:
// sherpa-onnx on mobile/desktop, Web Speech API on web.
export 'stt_factory_io.dart'
    if (dart.library.js_interop) 'stt_factory_web.dart';
