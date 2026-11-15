"""Eval runner: compare models on extraction, fit agreement and (with --full) hallucinations.

    cd backend
    uv run python ../evals/run_evals.py --model gemini/gemini-flash-latest
    uv run python ../evals/run_evals.py --model gemini/gemini-flash-latest --full --limit 3

Always uses the fictional sample profile (gold labels are relative to it).
Results are printed and written to evals/results/<date>_<model>.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from statistics import mean

EVALS = Path(__file__).resolve().parent
sys.path[:0] = [str(EVALS.parent / "backend"), str(EVALS.parent)]

from app.agent import nodes  # noqa: E402
from app.agent.graph import build_graph  # noqa: E402
from app.config import settings  # noqa: E402
from app.llm import track_usage  # noqa: E402
from app.profile import load_profile  # noqa: E402
from app.runs import Runs  # noqa: E402
from evals.metrics import (  # noqa: E402
    count_lines,
    extraction_counts,
    fit_bucket,
    precision_recall,
)

DATASET = EVALS / "dataset" / "postings.jsonl"
RESULTS = EVALS / "results"
AUTO_ANSWERS = {
    "paste_text": None,  # dataset cases are pasted text, never URLs
    "clarify": {"answer": "No further details are available."},
    "low_fit": {"proceed": True},
}


@dataclass
class ModelReport:
    model: str
    tp: int = 0
    fp: int = 0
    fn: int = 0
    vague_correct: int = 0
    fit_pairs: list[tuple[str, str, str]] = field(default_factory=list)  # (id, gold, predicted)
    lines: int = 0
    residual_flagged: int = 0
    first_pass_ok: int = 0
    full_runs: int = 0
    attempts: list[int] = field(default_factory=list)
    calls: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def load_cases(limit: int | None) -> list[dict]:
    cases = [json.loads(line) for line in DATASET.read_text().splitlines() if line.strip()]
    return cases[:limit] if limit else cases


def eval_extraction_and_fit(report: ModelReport, case: dict) -> None:
    state = {"posting_text": case["text"]}
    posting = nodes.extract_requirements(state)["posting"]
    report.vague_correct += posting.is_vague == case["gold_vague"]
    if case["gold_vague"]:
        return
    gold = [g["text"] for g in case["gold_requirements"]]
    tp, fp, fn = extraction_counts(gold, [r.text for r in posting.requirements])
    report.tp, report.fp, report.fn = report.tp + tp, report.fp + fp, report.fn + fn
    if case["gold_fit"]:
        fit = nodes.match_profile({**state, "posting": posting})["fit"]
        report.fit_pairs.append((case["id"], case["gold_fit"], fit_bucket(fit.score)))


def eval_full_pipeline(report: ModelReport, case: dict) -> None:
    """Run the whole graph, auto-answering questions, and inspect the final verification."""
    runs = Runs(build_graph())
    view = runs.start(posting_text=case["text"])
    while view.status == "waiting" and view.waiting_for.type in AUTO_ANSWERS:
        view = runs.answer(view.run_id, AUTO_ANSWERS[view.waiting_for.type])
    if view.status == "error":
        raise RuntimeError(view.error)
    if view.status != "waiting" or view.waiting_for.type != "approve":
        return
    attempts = sum(1 for c in view.usage.calls if c.step == "verify") or 1
    report.full_runs += 1
    report.attempts.append(attempts)
    report.lines += count_lines(view.cv, view.cover_letter)
    report.residual_flagged += len(view.verification.issues)
    report.first_pass_ok += attempts == 1 and view.verification.passed


def evaluate(model: str, cases: list[dict], full: bool) -> ModelReport:
    settings.model = model
    settings.verifier_model = None
    report = ModelReport(model)
    with track_usage() as calls:
        for case in cases:
            try:
                eval_extraction_and_fit(report, case)
                if full and not case["gold_vague"]:
                    eval_full_pipeline(report, case)
            except Exception as e:  # keep going: one provider hiccup shouldn't kill the run
                report.errors.append(f"{case['id']}: {type(e).__name__}: {str(e)[:200]}")
            print(f"  {model} {case['id']} done", file=sys.stderr)
    report.calls = calls
    return report


def to_markdown(reports: list[ModelReport], cases: list[dict], full: bool) -> str:
    head = "| Model | Extraction P | Extraction R | Vague detection | Fit agreement |"
    sep = "|---|---|---|---|---|"
    if full:
        head += " First-pass verified | Residual flagged lines | Avg verify attempts |"
        sep += "---|---|---|"
    head += " Calls | Cost (USD) | Avg latency/call (s) |"
    sep += "---|---|---|"
    rows = [head, sep]
    for r in reports:
        p, rec = precision_recall(r.tp, r.fp, r.fn)
        agree = sum(g == pred for _, g, pred in r.fit_pairs)
        cols = [
            r.model,
            f"{p:.2f}",
            f"{rec:.2f}",
            f"{r.vague_correct}/{len(cases)}",
            f"{agree}/{len(r.fit_pairs)}",
        ]
        if full:
            cols += [
                f"{r.first_pass_ok}/{r.full_runs}",
                f"{r.residual_flagged}/{r.lines}",
                f"{mean(r.attempts):.2f}" if r.attempts else "-",
            ]
        cost = sum(c["cost_usd"] or 0 for c in r.calls)
        lat = mean(c["latency_s"] for c in r.calls) if r.calls else 0
        cols += [str(len(r.calls)), f"{cost:.4f}", f"{lat:.1f}"]
        rows.append("| " + " | ".join(cols) + " |")

    out = [f"# Eval results — {date.today()}", "", f"{len(cases)} cases, sample profile.", ""]
    out += rows
    for r in reports:
        misses = [f"{i}: gold {g}, got {p}" for i, g, p in r.fit_pairs if g != p]
        if misses or r.errors:
            out += ["", f"## {r.model}"]
            out += [f"- fit miss — {m}" for m in misses]
            out += [f"- error — {e}" for e in r.errors]
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--model", action="append", required=True, help="LiteLLM model (repeatable)")
    ap.add_argument("--limit", type=int, help="only the first N cases")
    ap.add_argument("--full", action="store_true", help="also run generation + verification")
    args = ap.parse_args()

    settings.profile_path = settings.sample_profile_path
    load_profile.cache_clear()
    cases = load_cases(args.limit)

    reports = [evaluate(m, cases, args.full) for m in args.model]
    md = to_markdown(reports, cases, args.full)
    print(md)
    RESULTS.mkdir(exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", "_".join(args.model).lower()).strip("-")
    (RESULTS / f"{date.today()}_{slug}.md").write_text(md)


if __name__ == "__main__":
    main()
