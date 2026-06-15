import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:silvertech_mobile/vision/frame_source_file.dart';

void main() {
  test('returns the injected bytes on each grab', () async {
    final bytes = Uint8List.fromList(<int>[1, 2, 3, 4]);
    var loads = 0;
    final source = FileFrameSource(loader: () async {
      loads++;
      return bytes;
    });

    await source.start();
    expect(await source.grabFrame(), bytes);
    expect(await source.grabFrame(), bytes);
    expect(loads, 1); // cached after start
    await source.stop();
  });
}
