"""Eval runner skeleton (week 4). Extraction eval implemented; others TODO."""

from __future__ import annotations

import argparse
import json
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.agent import prompts  # noqa: E402
from app.llm import structured, usage  # noqa: E402
from app.schemas import JobPosting  # noqa: E402

DATASET = Path(__file__).parent / "dataset" / "postings.jsonl"


def similar(a: str, b: str) -> bool:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() > 0.6 or a.lower() in b.lower()


def eval_extraction(model: str, cases: list[dict]) -> dict:
    tp = fp = fn = 0
    for case in cases:
        pred = structured(
            JobPosting, system=prompts.EXTRACT, user=case["text"], step="extract", model=model
        )
        gold = [g["text"] for g in case["gold_requirements"]]
        got = [r.text for r in pred.requirements]
        matched_gold = {g for g in gold if any(similar(g, p) for p in got)}
        tp += len(matched_gold)
        fn += len(gold) - len(matched_gold)
        fp += sum(1 for p in got if not any(similar(g, p) for g in gold))
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    return {"precision": round(precision, 2), "recall": round(recall, 2)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", action="append", required=True)
    args = ap.parse_args()
    cases = [json.loads(line) for line in DATASET.read_text().splitlines() if line.strip()]

    print("| Model | Extraction P | Extraction R | Cost (USD) | Avg latency (s) |")
    print("|---|---|---|---|---|")
    for model in args.model:
        usage.calls.clear()
        r = eval_extraction(model, cases)
        avg_lat = sum(c.latency_s for c in usage.calls) / max(len(usage.calls), 1)
        print(
            f"| {model} | {r['precision']} | {r['recall']} | {usage.total_cost:.4f} | {avg_lat:.1f} |"
        )
    # TODO: hallucination rate, fit agreement


if __name__ == "__main__":
    main()
