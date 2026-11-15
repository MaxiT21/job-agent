"""Interactive terminal runner: the whole agent without the web UI.

    uv run python -m app.cli run --url https://...      # or --file posting.txt / --text "..."
    uv run python -m app.cli resume <run-id>             # continue a paused or failed run
    uv run python -m app.cli applications                # tracker

Uses the same persistent graph as the API, so runs started here show up there too.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, TextIO

from pydantic import ValidationError

from app import tracker
from app.api.models import RunView
from app.runs import RunNotFound, Runs


class _Console:
    def __init__(self, input_fn: Callable[[str], str], out: TextIO):
        self.input, self.out = input_fn, out

    def say(self, text: str = "") -> None:
        print(text, file=self.out)

    def ask(self, prompt: str) -> str:
        self.out.write(prompt)
        self.out.flush()
        return self.input("").strip()

    def yes(self, prompt: str) -> bool:
        return self.ask(f"{prompt} [y/N] ").lower() in ("y", "yes", "s", "si", "sí")

    def multiline(self, prompt: str) -> str:
        self.say(f"{prompt} (finish with an empty line)")
        lines = []
        while line := self.input(""):
            lines.append(line)
        return "\n".join(lines)


def _print_fit(c: _Console, view: RunView) -> None:
    if not view.fit:
        return
    reqs = {r.id: r for r in view.posting.requirements} if view.posting else {}
    c.say(f"\nFit score: {view.fit.score}")
    for m in view.fit.matches:
        req = reqs.get(m.requirement_id)
        label = f"{req.text} ({req.importance})" if req else ""
        evidence = ", ".join(m.evidence_ids) or "-"
        c.say(f"  {m.requirement_id:<4} {m.status:<8} {label:<40} evidence: {evidence}")
    c.say(f"  {view.fit.summary}")


def _print_documents(c: _Console, view: RunView) -> None:
    if view.cv:
        c.say("\n--- CV ---")
        c.say(view.cv.summary.text)
        for entry in view.cv.entries:
            c.say(f"\n[{entry.item_id}]")
            for b in entry.bullets:
                c.say(f"  • {b.text}   ({', '.join(b.evidence_ids)})")
        c.say(f"\nSkills: {', '.join(view.cv.skills)}")
    if view.cover_letter:
        c.say("\n--- Cover letter ---")
        for p in view.cover_letter.paragraphs:
            c.say(f"{p.text}\n")
    if view.verification:
        if view.verification.passed:
            c.say("Verification: passed ✓")
        else:
            c.say("Verification: ISSUES (review before approving)")
            for i in view.verification.issues:
                c.say(f"  ! {i.where}: {i.reason} — {i.text}")


def _answer(c: _Console, view: RunView) -> dict[str, Any]:
    w = view.waiting_for
    if w.type == "paste_text":
        c.say(f"\nCould not read the URL: {w.reason}")
        return {"text": c.multiline("Paste the posting text")}
    if w.type == "clarify":
        c.say(f"\nThe posting is vague. {w.question}")
        return {"answer": c.ask("> ")}
    if w.type == "low_fit":
        _print_fit(c, view)
        return {"proceed": c.yes("\nLow fit. Apply anyway?")}
    _print_fit(c, view)
    _print_documents(c, view)
    choice = c.ask("\nApprove? [y = approve / e = request edits / N = stop here] ").lower()
    if choice in ("y", "yes"):
        return {"approved": True}
    if choice == "e":
        return {"approved": False, "notes": c.ask("What should change? ")}
    raise KeyboardInterrupt


def _drive(c: _Console, runs: Runs, view: RunView) -> int:
    """Answer questions until the run finishes, stops or fails."""
    try:
        while view.status == "waiting":
            try:
                view = runs.answer(view.run_id, _answer(c, view))
            except ValidationError as e:
                c.say(f"Invalid answer: {e.errors()[0]['msg']}")
    except KeyboardInterrupt:
        c.say(f"\nPaused. Continue later with: python -m app.cli resume {view.run_id}")
        return 0

    if view.status == "error":
        c.say(f"\nStep failed: {view.error}")
        c.say(f"Fix the cause (API key, quota...) and run: python -m app.cli resume {view.run_id}")
        return 1
    if view.status == "stopped" and view.fit:
        _print_fit(c, view)
    c.say(f"\nStatus: {view.status}")
    if view.status == "done":
        c.say(f"CV: {runs.file_path(view.run_id, 'cv')}")
        if letter := runs.file_path(view.run_id, "cover_letter"):
            c.say(f"Cover letter: {letter}")
    u = view.usage
    c.say(f"LLM calls: {len(u.calls)} · cost ${u.total_cost_usd:.4f} · {u.total_latency_s:.1f}s")
    return 0


def main(
    argv: list[str] | None = None,
    *,
    input_fn: Callable[[str], str] = input,
    out: TextIO = sys.stdout,
    graph: Any = None,
) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="start a new application")
    src = run.add_mutually_exclusive_group(required=True)
    src.add_argument("--url")
    src.add_argument("--file", type=Path)
    src.add_argument("--text")
    sub.add_parser("resume", help="continue a paused or failed run").add_argument("run_id")
    sub.add_parser("applications", help="list tracked applications")
    args = parser.parse_args(argv)

    c = _Console(input_fn, out)
    if args.cmd == "applications":
        for a in tracker.list_applications():
            c.say(
                f"{a.created_at:%Y-%m-%d}  {a.status:<10} {a.fit_score:>5}  {a.company} — {a.title}"
            )
        return 0

    if graph is None:
        from app.agent.graph import get_graph

        graph = get_graph()
    runs = Runs(graph)

    if args.cmd == "run":
        text = args.file.read_text(encoding="utf-8") if args.file else args.text
        c.say("Working… (extracting requirements, matching, tailoring, verifying)")
        view = runs.start(posting_url=args.url, posting_text=text)
        c.say(f"Run id: {view.run_id}")
        return _drive(c, runs, view)

    try:
        view = runs.view(args.run_id)
    except RunNotFound:
        c.say(f"No run with id {args.run_id}")
        return 1
    if view.status == "error":
        view = runs.retry(args.run_id)
    return _drive(c, runs, view)


if __name__ == "__main__":
    sys.exit(main())
