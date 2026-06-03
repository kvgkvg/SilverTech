# On-device ASR model (Vietnamese)

The app uses **sherpa-onnx** with the
`sherpa-onnx-zipformer-vi-30M-int8-2026-02-09` offline transducer model.

These 4 files must live in this directory before `flutter build` (they are
listed as assets in `pubspec.yaml`). They are **not** committed (~32 MB).

```
encoder.int8.onnx   (~26 MB)
decoder.onnx        (~4.9 MB)
joiner.int8.onnx    (~1.0 MB)
tokens.txt          (~23 KB)
```

## Download

```bash
cd apps/mobile/assets/models/asr
wget https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-zipformer-vi-30M-int8-2026-02-09.tar.bz2
tar xjf sherpa-onnx-zipformer-vi-30M-int8-2026-02-09.tar.bz2 --strip-components=1 \
  sherpa-onnx-zipformer-vi-30M-int8-2026-02-09/encoder.int8.onnx \
  sherpa-onnx-zipformer-vi-30M-int8-2026-02-09/decoder.onnx \
  sherpa-onnx-zipformer-vi-30M-int8-2026-02-09/joiner.int8.onnx \
  sherpa-onnx-zipformer-vi-30M-int8-2026-02-09/tokens.txt
rm sherpa-onnx-zipformer-vi-30M-int8-2026-02-09.tar.bz2
```

(Confirm the exact release URL/tag at
<https://k2-fsa.github.io/sherpa/onnx/pretrained_models/offline-transducer/zipformer-transducer-models.html>.)

At runtime `SherpaRecognizer` copies these into the app documents dir on first
launch (sherpa-onnx needs real filesystem paths, not Flutter asset keys).
