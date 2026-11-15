"""Record real agent runs on the fictional sample profile for the public demo.

    cd backend && uv run python -m scripts.record_demo            # all scenarios
    cd backend && uv run python -m scripts.record_demo vague      # just one

Needs a provider key (real LLM calls). Writes frontend/public/demo/<id>.json (every pause of
the run plus the answer given), the rendered .docx files, and index.json. Refuses to run if a
real profile would be used: the demo must only ever contain the fictional candidate.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.agent.graph import build_graph
from app.api.models import RunView
from app.config import settings
from app.profile import load_profile, profile_source
from app.profile_builder import GUIDED_SECTIONS
from app.runs import Runs

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "frontend" / "public" / "demo"
DATASET = REPO / "evals" / "dataset" / "postings.jsonl"


class RealProfileError(RuntimeError):
    pass


@dataclass
class AutoAnswers:
    clarify: str = "No further details are available."
    proceed: bool = True
    paste_text: str | None = None


@dataclass
class Scenario:
    id: str
    title: str
    description: str
    posting_text: str
    answers: AutoAnswers = field(default_factory=AutoAnswers)


def _answer(waiting: Any, answers: AutoAnswers) -> dict:
    match waiting.type:
        case "clarify":
            return {"answer": answers.clarify}
        case "low_fit":
            return {"proceed": answers.proceed}
        case "approve":
            return {"approved": True}
        case "paste_text" if answers.paste_text:
            return {"text": answers.paste_text}
    raise RuntimeError(f"No scripted answer for {waiting.type}")


def _public(view: RunView, scenario_id: str) -> dict:
    data = view.model_dump(mode="json")
    data["run_id"] = scenario_id
    data["created_at"] = None
    return data


def record(scenario: Scenario, out_dir: Path) -> dict:
    """Run one scenario to the end, answering every question, and save the recording."""
    if profile_source() != "sample":
        raise RealProfileError(
            "A real profile is configured (data/profile.yaml). The demo must use the sample profile."
        )
    runs = Runs(build_graph())
    view = runs.start(posting_text=scenario.posting_text)
    steps: list[dict] = []
    while True:
        if view.status == "error":
            raise RuntimeError(f"{scenario.id}: {view.error}")
        if view.status != "waiting":
            steps.append({"view": _public(view, scenario.id), "answer": None})
            break
        answer = _answer(view.waiting_for, scenario.answers)
        steps.append({"view": _public(view, scenario.id), "answer": answer})
        view = runs.answer(view.run_id, answer)

    files_dir = out_dir / scenario.id
    files_dir.mkdir(parents=True, exist_ok=True)
    for kind, name in (("cv", "cv.docx"), ("cover_letter", "cover_letter.docx")):
        if path := runs.file_path(view.run_id, kind):
            shutil.copyfile(path, files_dir / name)

    recording = {
        "id": scenario.id,
        "title": scenario.title,
        "description": scenario.description,
        "posting_text": scenario.posting_text,
        "profile": load_profile().model_dump(mode="json"),
        "steps": steps,
    }
    (out_dir / f"{scenario.id}.json").write_text(
        json.dumps(recording, indent=1, ensure_ascii=False) + "\n"
    )
    return recording


def _posting(case_id: str) -> str:
    for line in DATASET.read_text().splitlines():
        case = json.loads(line)
        if case["id"] == case_id:
            return case["text"]
    raise KeyError(case_id)


def scenarios() -> list[Scenario]:
    return [
        Scenario(
            "strong-match",
            "Strong match",
            "A backend internship that fits the profile: evidence for every requirement.",
            _posting("p01"),
        ),
        Scenario(
            "low-fit",
            "Low fit",
            "A senior SRE role: the agent flags the gaps and asks before tailoring anything.",
            _posting("p03"),
        ),
        Scenario(
            "vague",
            "Vague posting",
            "A posting with no real requirements: the agent asks instead of guessing.",
            _posting("p08"),
            AutoAnswers(
                clarify="It's a junior backend developer role: Python, SQL and REST APIs, in Barcelona."
            ),
        ),
        Scenario(
            "spanish",
            "Spanish posting",
            "A QA internship in Spanish: the CV and letter come out in Spanish.",
            _posting("p02"),
        ),
        Scenario(
            "ai-intern",
            "AI engineer intern",
            "Partial fit: honest about the gaps, strict about the evidence.",
            _posting("p04"),
        ),
    ]


def main(only: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        settings.output_dir = Path(tmp) / "outputs"
        settings.database_path = Path(tmp) / "demo.db"
        chosen = [s for s in scenarios() if not only or s.id in only]
        for s in chosen:
            print(f"recording {s.id}…", flush=True)
            rec = record(s, OUT)
            history = rec["steps"][-1]["view"]["verification_history"]
            caught = sum(len(v["issues"]) for v in history if not v["passed"])
            print(f"  {len(rec['steps'])} steps, verifier caught {caught} issue(s)", flush=True)
    index = {
        "scenarios": [
            {"id": s.id, "title": s.title, "description": s.description}
            for s in scenarios()
            if (OUT / f"{s.id}.json").exists()
        ],
        "questions": [q.model_dump(mode="json") for q in GUIDED_SECTIONS],
    }
    (OUT / "index.json").write_text(json.dumps(index, indent=1) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
