# Known Limitations

- STT and LLM providers use mock implementations by default.
- Flutter is installed at `$HOME/development/flutter` and Flutter tests pass
  when `$HOME/development/flutter/bin` is used. The Flutter binary is not on the
  default shell PATH yet.
- OpenCV is installed in the `silvertech` environment. Synthetic tests still use
  deterministic keypoint arrays; real-image ORB validation needs reviewed panel
  photos.
- Real appliance images are not committed; placeholders document where reviewed
  panel images should be added before real-device validation.
- Crowdsourcing review is functional at API level but does not yet create full
  official templates from edited submissions.
