# Known Limitations

- STT and LLM providers use mock implementations by default.
- Flutter is scaffolded but not compiled in this environment because Flutter is
  not available from the configured Conda channels. Dart SDK is installed in the
  `silvertech` environment and pure Dart mobile logic tests pass.
- OpenCV is installed in the `silvertech` environment. Synthetic tests still use
  deterministic keypoint arrays; real-image ORB validation needs reviewed panel
  photos.
- Real appliance images are not committed; placeholders document where reviewed
  panel images should be added.
- Crowdsourcing review is functional at API level but does not yet create full
  official templates from edited submissions.
