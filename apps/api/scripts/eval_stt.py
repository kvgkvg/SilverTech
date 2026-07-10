"""Voice (STT) evaluation.

Two modes:

**Audio mode** (`--manifest`): a manifest lists recorded utterances with
reference transcripts; each file runs through `STTService.transcribe` and
is scored with WER/CER. Only meaningful once a real STT provider is
configured — the mock returns a fixed sentence and the script warns.

    manifest.json: [{"audio": "path.wav", "reference_vi": "...",
                     "template_id": "...", "case_id": "..."}, ...]

**Text-robustness mode** (default, no audio needed): simulates typical
Vietnamese STT errors on the golden-set queries — tone-mark loss, full
diacritic loss, dropped words — and measures how much guidance quality
degrades versus the clean transcript. This isolates the downstream
pipeline's sensitivity to STT noise, which is evaluable today.

Perturbation levels:
  clean          original query (baseline)
  tone_loss      tone marks stripped from ~40% of words (mild STT error)
  no_diacritics  all diacritics stripped (worst-case tone recognition)
  drop_word      one non-initial word dropped (truncation / VAD cut)
  noisy          no_diacritics + drop_word combined

Also writes `data/eval/stt/recording_script.md`: the utterance list to
record (elderly speakers if possible) for a future real-audio WER run.

Usage (repo root, silvertech conda env):
    PYTHONPATH=apps/api python apps/api/scripts/eval_stt.py
    PYTHONPATH=apps/api python apps/api/scripts/eval_stt.py --manifest data/eval/stt/manifest.json
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

from app.services.guidance_service import GuidanceError, create_guidance  # noqa: E402
from app.services.stt_service import STTService  # noqa: E402

TONE_MARKS = {"̀", "́", "̃", "̉", "̣"}


# --------------------------------------------------------------------------
# Perturbations (simulated STT errors)
# --------------------------------------------------------------------------

def strip_tones(word: str) -> str:
    """Remove tone marks only; keeps vowel shape (a^, o+, ...) and d-."""
    decomposed = unicodedata.normalize("NFD", word)
    return unicodedata.normalize(
        "NFC", "".join(ch for ch in decomposed if ch not in TONE_MARKS)
    )


def strip_diacritics(word: str) -> str:
    decomposed = unicodedata.normalize("NFD", word)
    flat = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return flat.replace("đ", "d").replace("Đ", "D")


def perturb(query: str, level: str, rng: random.Random) -> str:
    words = query.split()
    if level == "clean":
        return query
    if level == "tone_loss":
        return " ".join(
            strip_tones(w) if rng.random() < 0.4 else w for w in words
        )
    if level == "no_diacritics":
        return " ".join(strip_diacritics(w) for w in words)
    if level == "drop_word":
        if len(words) > 3:
            words.pop(rng.randrange(1, len(words)))
        return " ".join(words)
    if level == "noisy":
        words = [strip_diacritics(w) for w in words]
        if len(words) > 3:
            words.pop(rng.randrange(1, len(words)))
        return " ".join(words)
    raise ValueError(level)


LEVELS = ["clean", "tone_loss", "no_diacritics", "drop_word", "noisy"]


# --------------------------------------------------------------------------
# WER / CER
# --------------------------------------------------------------------------

def edit_distance(ref: list, hyp: list) -> int:
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h))
        prev = cur
    return prev[-1]


def wer(reference: str, hypothesis: str) -> float:
    ref = reference.lower().split()
    return edit_distance(ref, hypothesis.lower().split()) / max(1, len(ref))


def cer(reference: str, hypothesis: str) -> float:
    ref = list(reference.lower())
    return edit_distance(ref, list(hypothesis.lower())) / max(1, len(ref))


# --------------------------------------------------------------------------
# Guidance scoring (same definition as eval_guidance.py)
# --------------------------------------------------------------------------

def score_guidance(case: dict, query: str) -> dict:
    required = set(case["expected_buttons"])
    allowed = required | set(case["allowed_extra"])
    outcome, payload = "accepted", None
    try:
        payload = create_guidance(case["template_id"], query)
    except GuidanceError as exc:
        outcome = str(exc)
    steps = payload.get("steps", []) if payload else []
    predicted = {s["button_id"] for s in steps}
    refused = payload is not None and payload.get("intent") == "out_of_scope" and not steps
    if case["expect_out_of_scope"]:
        correct = refused
    else:
        correct = (
            payload is not None
            and not refused
            and required <= predicted
            and predicted <= allowed
        )
    return {
        "outcome": outcome,
        "gate": outcome != "invalid_button",
        "correct": bool(correct),
        "predicted": " ".join(sorted(predicted)),
    }


# --------------------------------------------------------------------------
# Modes
# --------------------------------------------------------------------------

def run_robustness(golden_path: Path, out_dir: Path, provider: str) -> None:
    golden = json.loads(golden_path.read_text())["cases"]
    rows = []
    for case in golden:
        rng = random.Random(case["id"])  # deterministic per case
        for level in LEVELS:
            query = perturb(case["query_vi"], level, rng)
            score = score_guidance(case, query)
            rows.append(
                {
                    "case_id": case["id"],
                    "level": level,
                    "query": query,
                    "query_wer_vs_clean": round(wer(case["query_vi"], query), 3),
                    **score,
                }
            )
    fields = ["case_id", "level", "query", "query_wer_vs_clean", "outcome", "gate", "correct", "predicted"]
    with (out_dir / "results.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (out_dir / "results.json").write_text(
        json.dumps({"mode": "text_robustness", "provider": provider, "rows": rows},
                   indent=2, ensure_ascii=False)
    )

    lines = [
        "# STT robustness evaluation (simulated transcription errors)",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"LLM provider: **{provider}**  |  STT: simulated errors (no audio)",
        f"Golden cases: {len(golden)} x {len(LEVELS)} perturbation levels",
        "",
        "## Method",
        "",
        "Real STT is not connected, so this measures the DOWNSTREAM half of the",
        "voice path: typical Vietnamese STT errors (tone loss, full diacritic",
        "loss, dropped words) are injected into the golden-set queries and each",
        "noisy transcript runs through the full guidance path. The drop from the",
        "`clean` row is the pipeline's sensitivity to STT noise. Acoustic WER of",
        "a real provider needs recorded audio — see `recording_script.md`.",
        "",
        "## Correct-guidance rate per noise level",
        "",
        "| level | simulated WER | gate pass | correct | delta vs clean |",
        "|---|---|---|---|---|",
    ]
    mean = lambda xs: sum(xs) / len(xs) if xs else 0.0  # noqa: E731
    clean_correct = mean([r["correct"] for r in rows if r["level"] == "clean"])
    for level in LEVELS:
        sub = [r for r in rows if r["level"] == level]
        corr = mean([r["correct"] for r in sub])
        lines.append(
            f"| {level} | {mean([r['query_wer_vs_clean'] for r in sub]):.2f} | "
            f"{mean([r['gate'] for r in sub]):.0%} | {corr:.0%} | "
            f"{corr - clean_correct:+.0%} |"
        )
    lines += [
        "",
        "## Caveats",
        "",
        "- Simulated errors model tone/diacritic loss and truncation only; real",
        "  STT also substitutes phonetically similar words.",
        "- With the mock LLM provider, absolute rates reflect the keyword-matcher",
        "  baseline; the DELTA column is the meaningful robustness signal.",
        "- For acoustic WER: record `recording_script.md` utterances, build a",
        "  manifest, connect a real STT provider, rerun with `--manifest`.",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines))


def run_audio(manifest_path: Path, out_dir: Path) -> None:
    provider = os.getenv("SILVERTECH_STT_PROVIDER", "mock").strip().lower()
    if provider == "mock":
        print("WARNING: SILVERTECH_STT_PROVIDER=mock returns a fixed sentence; "
              "WER below is meaningless. Connect a real provider first.")
    manifest = json.loads(manifest_path.read_text())
    stt = STTService()
    rows = []
    for item in manifest:
        audio = (ROOT / item["audio"]).read_bytes()
        text, confidence = stt.transcribe(audio)
        rows.append(
            {
                "case_id": item.get("case_id", item["audio"]),
                "audio": item["audio"],
                "reference": item["reference_vi"],
                "hypothesis": text,
                "confidence": confidence,
                "wer": round(wer(item["reference_vi"], text), 3),
                "cer": round(cer(item["reference_vi"], text), 3),
            }
        )
        print(f"{item['audio']}: WER={rows[-1]['wer']} CER={rows[-1]['cer']}")
    fields = list(rows[0].keys()) if rows else []
    with (out_dir / "results.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (out_dir / "results.json").write_text(
        json.dumps({"mode": "audio", "provider": provider, "rows": rows},
                   indent=2, ensure_ascii=False)
    )
    mean_wer = sum(r["wer"] for r in rows) / len(rows) if rows else 0.0
    mean_cer = sum(r["cer"] for r in rows) / len(rows) if rows else 0.0
    (out_dir / "summary.md").write_text(
        "# STT audio evaluation\n\n"
        f"Generated: {datetime.now(timezone.utc).isoformat()}\n"
        f"Provider: **{provider}**  |  Utterances: {len(rows)}\n\n"
        f"- mean WER: **{mean_wer:.1%}**\n"
        f"- mean CER: **{mean_cer:.1%}**\n"
    )


def write_recording_script(golden_path: Path, dest: Path) -> None:
    golden = json.loads(golden_path.read_text())["cases"]
    lines = [
        "# STT recording script",
        "",
        "Record each utterance as one file (wav/m4a, quiet room + one noisy-room",
        "repeat if possible; elderly speakers preferred). Name files by ID.",
        "Then build `manifest.json`:",
        "",
        '```json',
        '[{"audio": "data/eval/stt/recordings/mw_grill_1.wav",',
        '  "reference_vi": "Làm sao để nướng gà?", "case_id": "mw_grill_1"}]',
        "```",
        "",
        "| file | utterance |",
        "|---|---|",
    ]
    for case in golden:
        if not case["expect_out_of_scope"]:
            lines.append(f"| {case['id']}.wav | {case['query_vi']} |")
    dest.write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden", default=str(ROOT / "data" / "eval" / "llm" / "golden_set.json"))
    parser.add_argument("--manifest", default=None, help="audio manifest -> WER mode")
    parser.add_argument("--out", default=str(ROOT / "data" / "eval" / "stt"))
    args = parser.parse_args()

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    write_recording_script(Path(args.golden), out_root / "recording_script.md")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = out_root / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.manifest:
        run_audio(Path(args.manifest), out_dir)
    else:
        provider = os.getenv("SILVERTECH_LLM_PROVIDER", "mock").strip().lower()
        run_robustness(Path(args.golden), out_dir, provider)
    print(f"\nwrote {out_dir}")


if __name__ == "__main__":
    main()
