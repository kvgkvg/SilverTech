"""Guidance (LLM) evaluation against the golden set.

Method:
  1. `data/eval/llm/golden_set.json` holds Vietnamese queries with the
     REQUIRED button_ids a correct answer must reference, ALLOWED extra
     helper buttons, and out-of-scope cases that must be refused. It is
     authored from the appliance manuals, independent of any provider.
  2. Each query runs through the real service path
     (`guidance_service.create_guidance`), i.e. prompt building, the LLM
     provider selected by SILVERTECH_LLM_PROVIDER, response parsing, the
     `validate_guidance_buttons` gate, and instruction humanization.
  3. Scored per case:
       gate            passed the button_id validation gate (no 409)
       scope_correct   refused when it should, answered when it should
       recall          |predicted ∩ required| / |required|
       precision       |predicted ∩ (required ∪ allowed)| / |predicted|
       correct         scope right AND recall==1 AND precision==1
       tts_safe        no raw button_id token appears in spoken text
       latency_ms
  4. A second section aggregates the production `llm_logs` table
     (accept/reject counts + latency), i.e. evaluation from real traffic.

Usage (repo root, silvertech conda env):
    PYTHONPATH=apps/api python apps/api/scripts/eval_guidance.py \
        [--golden data/eval/llm/golden_set.json] [--out data/eval/llm]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

from app.services.guidance_service import GuidanceError, create_guidance  # noqa: E402
from app.storage.database import DB_PATH  # noqa: E402

CSV_FIELDS = [
    "id", "template_id", "provider", "outcome", "gate", "scope_correct",
    "predicted_buttons", "recall", "precision", "correct", "tts_safe", "latency_ms",
]


def run_case(case: dict, provider: str) -> dict:
    required = set(case["expected_buttons"])
    allowed = required | set(case["allowed_extra"])
    started = time.perf_counter()
    outcome, payload = "accepted", None
    try:
        payload = create_guidance(case["template_id"], case["query_vi"])
    except GuidanceError as exc:
        outcome = str(exc)
    latency_ms = int((time.perf_counter() - started) * 1000)

    steps = payload.get("steps", []) if payload else []
    predicted = [s["button_id"] for s in steps]
    refused = payload is not None and payload.get("intent") == "out_of_scope" and not steps

    gate = outcome != "invalid_button"
    if case["expect_out_of_scope"]:
        scope_correct = refused
        recall = precision = 1.0 if refused else 0.0
    else:
        scope_correct = payload is not None and not refused
        pred_set = set(predicted)
        recall = len(pred_set & required) / len(required) if required else 1.0
        precision = len(pred_set & allowed) / len(pred_set) if pred_set else 0.0

    spoken = " ".join(
        f"{s.get('instruction_vi', '')} {s.get('expected_result', '')}" for s in steps
    )
    tts_safe = not any(
        re.search(rf"\b{re.escape(b)}\b", spoken) for b in predicted if len(b) > 2
    )

    return {
        "id": case["id"],
        "expect_oos": case["expect_out_of_scope"],
        "template_id": case["template_id"],
        "provider": provider,
        "outcome": outcome,
        "gate": gate,
        "scope_correct": bool(scope_correct),
        "predicted_buttons": " ".join(predicted),
        "recall": round(recall, 3),
        "precision": round(precision, 3),
        "correct": bool(scope_correct and recall == 1.0 and precision == 1.0),
        "tts_safe": tts_safe,
        "latency_ms": latency_ms,
        "_steps": steps,
        "_safety_note": (payload or {}).get("safety_note"),
    }


def llm_logs_stats() -> dict:
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            "SELECT validation_status, COUNT(*), AVG(latency_ms) FROM llm_logs "
            "GROUP BY validation_status"
        ).fetchall()
        latencies = [r[0] for r in conn.execute("SELECT latency_ms FROM llm_logs")]
    finally:
        conn.close()
    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95) - 1] if latencies else None
    return {
        "total": len(latencies),
        "by_status": {r[0]: {"count": r[1], "mean_latency_ms": round(r[2] or 0)} for r in rows},
        "p95_latency_ms": p95,
    }


def write_summary(out_dir: Path, provider: str, rows: list[dict], logs: dict) -> None:
    n = len(rows)
    guidance_rows = [r for r in rows if not r["expect_oos"]]
    oos_rows = [r for r in rows if r not in guidance_rows]
    mean = lambda xs: sum(xs) / len(xs) if xs else 0.0  # noqa: E731

    lines = [
        "# Guidance (LLM) golden-set evaluation",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Provider: **{provider}** (`SILVERTECH_LLM_PROVIDER`)",
        f"Cases: {n} ({len(guidance_rows)} guidance, {len(oos_rows)} out-of-scope)",
        "",
        "## Method",
        "",
        "Golden set (`data/eval/llm/golden_set.json`) authored from the appliance",
        "manuals: each Vietnamese query lists the REQUIRED button_ids a correct",
        "answer must reference and ALLOWED helper buttons; out-of-scope queries",
        "must be refused. Every query runs through the real service path",
        "(`create_guidance`): prompt build -> provider -> parse ->",
        "`validate_guidance_buttons` gate -> humanization. `correct` = scope",
        "handled right AND all required buttons present AND no button outside",
        "required+allowed.",
        "",
        "## Aggregates",
        "",
        f"- validation gate pass rate: **{mean([r['gate'] for r in rows]):.0%}**",
        f"- fully correct cases: **{mean([r['correct'] for r in rows]):.0%}** ({sum(r['correct'] for r in rows)}/{n})",
        f"- guidance cases — mean recall {mean([r['recall'] for r in guidance_rows]):.0%}, "
        f"mean precision {mean([r['precision'] for r in guidance_rows]):.0%}",
        f"- out-of-scope refusal accuracy: {mean([r['scope_correct'] for r in oos_rows]):.0%} "
        f"({sum(r['scope_correct'] for r in oos_rows)}/{len(oos_rows)})",
        f"- TTS-safe (no raw button_id spoken): {mean([r['tts_safe'] for r in rows]):.0%}",
        f"- mean latency: {mean([r['latency_ms'] for r in rows]):.0f} ms",
        "",
        "## Per-case results",
        "",
        "| case | outcome | scope | predicted | recall | precision | correct | ms |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['id']} | {r['outcome']} | {'Y' if r['scope_correct'] else 'N'} | "
            f"{r['predicted_buttons'] or '-'} | {r['recall']} | {r['precision']} | "
            f"{'Y' if r['correct'] else 'N'} | {r['latency_ms']} |"
        )
    lines += [
        "",
        "## Production llm_logs aggregate",
        "",
        f"- total logged attempts: {logs['total']}",
    ]
    for status, s in logs["by_status"].items():
        lines.append(f"- {status}: {s['count']} (mean latency {s['mean_latency_ms']} ms)")
    if logs["p95_latency_ms"] is not None:
        lines.append(f"- p95 latency: {logs['p95_latency_ms']} ms")
    lines += [
        "",
        "## Caveats",
        "",
        "- With the mock provider this measures the keyword-matcher baseline and",
        "  the correctness gates, NOT real LLM quality. Re-run with",
        "  `SILVERTECH_LLM_PROVIDER=openrouter` for provider evaluation.",
        "- Button-set metrics don't judge instruction wording quality; pair with",
        "  a small human rubric pass for the report.",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden", default=str(ROOT / "data" / "eval" / "llm" / "golden_set.json"))
    parser.add_argument("--out", default=str(ROOT / "data" / "eval" / "llm"))
    args = parser.parse_args()

    provider = os.getenv("SILVERTECH_LLM_PROVIDER", "mock").strip().lower()
    golden = json.loads(Path(args.golden).read_text())
    rows = []
    for case in golden["cases"]:
        row = run_case(case, provider)
        rows.append(row)
        print(
            f"{row['id']}: outcome={row['outcome']} correct={row['correct']} "
            f"pred=[{row['predicted_buttons']}] {row['latency_ms']}ms",
            flush=True,
        )

    logs = llm_logs_stats()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out) / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(
        json.dumps(
            {
                "provider": provider,
                "cases": [{k: v for k, v in r.items() if k != "_steps"} | {"steps": r["_steps"]} for r in rows],
                "llm_logs": logs,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    with (out_dir / "results.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows([{k: r[k] for k in CSV_FIELDS} for r in rows])
    write_summary(out_dir, provider, rows, logs)
    print(f"\nwrote {out_dir}")


if __name__ == "__main__":
    main()
