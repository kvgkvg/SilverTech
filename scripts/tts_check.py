#!/usr/bin/env python3
"""Check the TTS pipeline against arbitrary Vietnamese text.

Synthesises the text with the same TTSService the API uses, then transcribes the
resulting mp3 back with the on-device Vietnamese ASR model so the audio can be
checked without listening to it.

    python scripts/tts_check.py "Bấm nút khởi động để bắt đầu hâm nóng."
    python scripts/tts_check.py --play "Bấm nút 1 phút hai lần."
    python scripts/tts_check.py --from-query "Hâm nóng cơm trong 2 phút"

`--from-query` sends the query through the real /api/query pipeline (LLM +
button validation) and checks every step's audio, which is the end-to-end case.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

ASR_MODEL_DIR = ROOT / "apps" / "mobile" / "assets" / "models" / "asr"
DEMO_TEMPLATE_ID = "template_panasonic_microwave_nn_gt35hm_v1"


def synthesize(text: str) -> Path:
    from app.services.tts_service import TTSService

    url = TTSService().synthesize(text)
    return ROOT / "data" / "tts" / Path(url).name


def transcribe(mp3: Path) -> str:
    import numpy as np
    import sherpa_onnx

    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "audio.wav"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(mp3), "-ar", "16000", "-ac", "1", str(wav)],
            check=True,
        )
        with wave.open(str(wav)) as handle:
            pcm = np.frombuffer(handle.readframes(handle.getnframes()), dtype=np.int16)

    recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=str(ASR_MODEL_DIR / "encoder.int8.onnx"),
        decoder=str(ASR_MODEL_DIR / "decoder.onnx"),
        joiner=str(ASR_MODEL_DIR / "joiner.int8.onnx"),
        tokens=str(ASR_MODEL_DIR / "tokens.txt"),
        num_threads=4,
        sample_rate=16000,
        feature_dim=80,
    )
    stream = recognizer.create_stream()
    stream.accept_waveform(16000, pcm.astype(np.float32) / 32768.0)
    recognizer.decode_stream(stream)
    return stream.result.text.strip()


def check(text: str, *, play: bool) -> None:
    mp3 = synthesize(text)
    duration = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp3)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    print(f"text  : {text}")
    print(f"mp3   : {mp3.relative_to(ROOT)}  ({float(duration):.2f}s)")
    print(f"heard : {transcribe(mp3)}")
    if play:
        subprocess.run(["ffplay", "-v", "error", "-nodisp", "-autoexit", str(mp3)], check=False)
    print()


def steps_from_query(query: str) -> list[str]:
    import os

    from app.services.env_loader import load_env_file
    from app.services.guidance_service import create_guidance

    # Nothing imports app.main here, so .env has to be loaded by hand; without it
    # SILVERTECH_LLM_PROVIDER defaults to "mock" and the check silently proves
    # nothing about the real LLM.
    load_env_file()
    print(f"provider: {os.getenv('SILVERTECH_LLM_PROVIDER', 'mock')}")
    guidance = create_guidance(DEMO_TEMPLATE_ID, query)
    return [step["instruction_vi"] for step in guidance["steps"]]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("text", nargs="*", help="Vietnamese text to synthesise")
    parser.add_argument("--play", action="store_true", help="play the audio through ffplay")
    parser.add_argument("--from-query", help="run a real /api/query and check every step's audio")
    args = parser.parse_args()

    if args.from_query:
        for instruction in steps_from_query(args.from_query):
            check(instruction, play=args.play)
    elif args.text:
        check(" ".join(args.text), play=args.play)
    else:
        parser.error("pass some text, or --from-query")


if __name__ == "__main__":
    main()
