# Known Limitations

- Backend STT and LLM providers use mock implementations by default. LLM
  guidance can call OpenRouter when `SILVERTECH_LLM_PROVIDER=openrouter`,
  `OPENROUTER_API_KEY`, and `OPENROUTER_MODEL=qwen/qwen3.7-plus` are set.
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
