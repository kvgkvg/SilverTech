# STT robustness evaluation (simulated transcription errors)

Generated: 2026-07-10T08:02:19.995441+00:00
LLM provider: **mock**  |  STT: simulated errors (no audio)
Golden cases: 97 x 5 perturbation levels

## Method

Real STT is not connected, so this measures the DOWNSTREAM half of the
voice path: typical Vietnamese STT errors (tone loss, full diacritic
loss, dropped words) are injected into the golden-set queries and each
noisy transcript runs through the full guidance path. The drop from the
`clean` row is the pipeline's sensitivity to STT noise. Acoustic WER of
a real provider needs recorded audio — see `recording_script.md`.

## Correct-guidance rate per noise level

| level | simulated WER | gate pass | correct | delta vs clean |
|---|---|---|---|---|
| clean | 0.00 | 100% | 26% | +0% |
| tone_loss | 0.26 | 100% | 22% | -4% |
| no_diacritics | 0.70 | 100% | 26% | +0% |
| drop_word | 0.14 | 100% | 20% | -6% |
| noisy | 0.75 | 100% | 24% | -2% |

## Caveats

- Simulated errors model tone/diacritic loss and truncation only; real
  STT also substitutes phonetically similar words.
- With the mock LLM provider, absolute rates reflect the keyword-matcher
  baseline; the DELTA column is the meaningful robustness signal.
- For acoustic WER: record `recording_script.md` utterances, build a
  manifest, connect a real STT provider, rerun with `--manifest`.