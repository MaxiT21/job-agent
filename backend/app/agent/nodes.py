"""Graph nodes. Each takes the state and returns a partial update.

Nodes that call `interrupt()` pause the graph and wait for the user; the API
resumes them with `Command(resume=...)`.
"""

from __future__ import annotations

import httpx
from bs4 import BeautifulSoup
from langgraph.types import interrupt

from app.agent import prompts
from app.agent.state import AgentState
from app.config import settings
from app.cv.render import render_cv
from app.llm import structured
from app.profile import load_profile
from app.schemas import (
    CoverLetter,
    FitReport,
    JobPosting,
    MatchResult,
    TailoredCV,
    VerificationResult,
)
from app.scoring import check_evidence_ids, fit_score
from app.tracker import log_application


def _profile_json() -> str:
    return load_profile().model_dump_json(indent=1)


# ---------- 1. Input ----------


def fetch_posting(state: AgentState) -> dict:
    if state.get("posting_text"):
        return {"status": "running"}
    url = state.get("posting_url")
    if not url:
        raise ValueError("Provide posting_url or posting_text")
    html = httpx.get(
        url, timeout=20, follow_redirects=True, headers={"User-Agent": "job-agent/0.1"}
    ).text
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = " ".join(soup.get_text(" ").split())
    return {"posting_text": text[:20_000], "status": "running"}


def extract_requirements(state: AgentState) -> dict:
    user = state["posting_text"]
    if state.get("user_notes"):
        user += f"\n\nExtra context from the candidate: {state['user_notes']}"
    posting = structured(JobPosting, system=prompts.EXTRACT, user=user, step="extract")
    return {"posting": posting}


def ask_clarification(state: AgentState) -> dict:
    """Agent decision: the posting is too vague, ask the user instead of guessing."""
    answer = interrupt({"type": "clarify", "question": state["posting"].clarifying_question})
    return {"user_notes": str(answer)}


# ---------- 2. Matching ----------


def match_profile(state: AgentState) -> dict:
    posting = state["posting"]
    result = structured(
        MatchResult,
        system=prompts.MATCH,
        user=f"JOB:\n{posting.model_dump_json(indent=1)}\n\nPROFILE:\n{_profile_json()}",
        step="match",
    )
    score = fit_score(posting, result.matches)
    return {"fit": FitReport(matches=result.matches, summary=result.summary, score=score)}


def confirm_low_fit(state: AgentState) -> dict:
    """Agent decision: low fit -> ask whether it's worth applying."""
    fit = state["fit"]
    gaps = [m.requirement_id for m in fit.matches if m.status == "gap"]
    answer = interrupt(
        {"type": "low_fit", "score": fit.score, "gaps": gaps, "summary": fit.summary}
    )
    return {"status": "running" if answer.get("continue") else "stopped"}


# ---------- 3. Generation ----------


def _feedback_block(state: AgentState) -> str:
    parts = []
    if (v := state.get("verification")) and not v.passed:
        issues = "\n".join(f"- {i.where}: {i.reason} ({i.text})" for i in v.issues)
        parts.append(f"Fix these verifier issues:\n{issues}")
    if notes := state.get("user_notes"):
        parts.append(f"Candidate notes: {notes}")
    return "\n\n".join(parts)


def tailor_cv(state: AgentState) -> dict:
    posting, fit = state["posting"], state["fit"]
    cv = structured(
        TailoredCV,
        system=prompts.TAILOR.format(language=posting.language.value),
        user=(
            f"JOB:\n{posting.model_dump_json(indent=1)}\n\nFIT:\n{fit.model_dump_json(indent=1)}"
            f"\n\nPROFILE:\n{_profile_json()}\n\n{_feedback_block(state)}"
        ),
        step="tailor_cv",
    )
    return {"cv": cv}


def write_cover_letter(state: AgentState) -> dict:
    posting, fit = state["posting"], state["fit"]
    letter = structured(
        CoverLetter,
        system=prompts.COVER_LETTER.format(language=posting.language.value),
        user=(
            f"JOB:\n{posting.model_dump_json(indent=1)}\n\nFIT:\n{fit.model_dump_json(indent=1)}"
            f"\n\nPROFILE:\n{_profile_json()}\n\n{_feedback_block(state)}"
        ),
        step="cover_letter",
    )
    return {"cover_letter": letter}


# ---------- 4. Verification ----------


def verify(state: AgentState) -> dict:
    profile = load_profile()
    cv, letter = state["cv"], state.get("cover_letter")

    # Layer 1: deterministic, free, catches made-up IDs and skills.
    issues = check_evidence_ids(profile, cv, letter)

    # Layer 2: LLM fact-check of each line against the evidence it cites.
    if not issues:
        llm_check = structured(
            VerificationResult,
            system=prompts.VERIFY,
            user=f"CV:\n{cv.model_dump_json(indent=1)}\n\nLETTER:\n"
            f"{letter.model_dump_json(indent=1) if letter else 'none'}\n\nPROFILE:\n{_profile_json()}",
            step="verify",
            model=settings.verifier_model,
        )
        issues = llm_check.issues

    return {
        "verification": VerificationResult(passed=not issues, issues=issues),
        "verify_attempts": state.get("verify_attempts", 0) + 1,
    }


# ---------- 5. Approval + output ----------


def human_approval(state: AgentState) -> dict:
    answer = interrupt(
        {
            "type": "approve",
            "fit": state["fit"].model_dump(),
            "cv": state["cv"].model_dump(),
            "cover_letter": state["cover_letter"].model_dump()
            if state.get("cover_letter")
            else None,
            "verification": state["verification"].model_dump(),
        }
    )
    if answer.get("approved"):
        return {"status": "approved"}
    # Rejected with edit notes -> regenerate with them.
    return {"user_notes": answer.get("notes", ""), "verification": None, "verify_attempts": 0}


def render_and_log(state: AgentState) -> dict:
    path = render_cv(load_profile(), state["cv"], state["posting"])
    log_application(state["posting"], state["fit"].score, path)
    return {"cv_path": str(path), "status": "done"}
