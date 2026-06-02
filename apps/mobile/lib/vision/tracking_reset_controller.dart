class TrackingResetController {
  bool _resetRequested = false;
  bool get resetRequested => _resetRequested;
  void requestReset() => _resetRequested = true;
  void clear() => _resetRequested = false;
}
