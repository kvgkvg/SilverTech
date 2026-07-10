#!/usr/bin/env bash
# Builds the Flutter web bundle for a Vercel static deploy.
#
# The API base url is compiled in, so a new ngrok url means a rebuild. Point
# SILVERTECH_API_BASE_URL at the tunnel before running:
#
#   SILVERTECH_API_BASE_URL=https://alone-exuberant-tidy.ngrok-free.dev \
#     scripts/build_web.sh
#
# Then deploy the output, which already carries vercel.json:
#
#   vercel deploy --prod apps/mobile/build/web
set -euo pipefail

: "${SILVERTECH_API_BASE_URL:?set it to the backend origin, e.g. the ngrok url}"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mobile_dir="$repo_root/apps/mobile"
out_dir="$mobile_dir/build/web"

cd "$mobile_dir"
flutter build web --release \
  --dart-define="SILVERTECH_API_BASE_URL=$SILVERTECH_API_BASE_URL"

# pubspec declares the sherpa-onnx ASR models for the native builds, so the web
# build bundles 32MB the browser never fetches: `stt_factory.dart` swaps in the
# Web Speech API whenever `dart.library.js_interop` is available.
rm -rf "$out_dir/assets/assets/models/asr"

# `flutter build` wipes build/web, so the deploy config is copied in afterwards.
cp "$mobile_dir/vercel.json" "$out_dir/vercel.json"

echo
echo "built with API base url: $SILVERTECH_API_BASE_URL"
echo "bundle size: $(du -sh "$out_dir" | cut -f1)"
echo "deploy: vercel deploy --prod $out_dir"
