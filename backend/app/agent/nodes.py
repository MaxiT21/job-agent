"""Graph nodes. Each takes the state and returns a partial update.

Nodes that call `interrupt()` pause the graph and wait for the user; the API
resumes them with `Command(resume=...)`, validated against the matching *Answer model.
"""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt

from app.agent import prompts
from app.agent.prompts import fence
from app.agent.state import AgentState
from app.config import settings
from app.fetch import MAX_TEXT_CHARS, FetchError, fetch_posting_text
from app.llm import structured
from app.profile import load_profile
from app.render import render_cover_letter, render_cv, run_output_dir
from app.schemas import (
    ApprovalAnswer,
    ApprovalRequest,
    ClarifyAnswer,
    ClarifyRequest,
    CoverLetter,
    FitReport,
    JobPosting,
    LowFitAnswer,
    LowFitRequest,
    MatchResult,
    PasteTextAnswer,
    PasteTextRequest,
    TailoredCV,
    VerificationIssue,
    VerificationResult,
)
from app.scoring import check_evidence_ids, fit_score
from app.tracker import log_application

BOTH: list = ["cv", "letter"]


def _profile_json() -> str:
    return load_profile().model_dump_json(indent=1)


def _context(state: AgentState) -> str:
    """Trusted context from the candidate, shared by every prompt after extraction."""
    if clarifications := state.get("clarifications"):
        return "Candidate context (trusted):\n" + "\n".join(f"- {c}" for c in clarifications)
    return ""


# ---------- 1. Input ----------


def fetch_posting(state: AgentState) -> dict:
    if text := state.get("posting_text"):
        return {"posting_text": text[:MAX_TEXT_CHARS], "status": "running"}
    url = state.get("posting_url")
    if not url:
        raise ValueError("Provide posting_url or posting_text")
    try:
        return {"posting_text": fetch_posting_text(url), "status": "running"}
    except FetchError as e:
        return {"fetch_error": str(e), "status": "running"}


def ask_for_text(state: AgentState) -> dict:
    """The URL could not be read: ask the candidate to paste the posting instead of failing."""
    raw = interrupt(PasteTextRequest(reason=state["fetch_error"]).model_dump(mode="json"))
    text = PasteTextAnswer.model_validate(raw).text
    return {"posting_text": text[:MAX_TEXT_CHARS], "fetch_error": None}


def extract_requirements(state: AgentState) -> dict:
    user = "\n\n".join(filter(None, [fence(state["posting_text"]), _context(state)]))
    posting = structured(JobPosting, system=prompts.EXTRACT, user=user, step="extract")
    return {"posting": posting}


def ask_clarification(state: AgentState) -> dict:
    """Agent decision: the posting is too vague, ask the user instead of guessing."""
    question = state["posting"].clarifying_question
    raw = interrupt(ClarifyRequest(question=question).model_dump(mode="json"))
    return {"clarifications": [ClarifyAnswer.model_validate(raw).answer]}


# ---------- 2. Matching ----------


def match_profile(state: AgentState) -> dict:
    posting = state["posting"]
    result = structured(
        MatchResult,
        system=prompts.MATCH,
        user=f"JOB:\n{fence(posting.model_dump_json(indent=1))}\n\nPROFILE:\n{_profile_json()}",
        step="match",
    )
    score = fit_score(posting, result.matches)
    return {"fit": FitReport(matches=result.matches, summary=result.summary, score=score)}


def confirm_low_fit(state: AgentState) -> dict:
    """Agent decision: low fit -> ask whether it's worth applying."""
    fit = state["fit"]
    gaps = [m.requirement_id for m in fit.matches if m.status == "gap"]
    answer = interrupt(
        LowFitRequest(score=fit.score, gaps=gaps, summary=fit.summary).model_dump(mode="json")
    )
    proceed = LowFitAnswer.model_validate(answer).proceed
    return {"status": "running" if proceed else "stopped"}


# ---------- 3. Generation ----------


def _issues_for(state: AgentState, target: str) -> list[VerificationIssue]:
    v = state.get("verification")
    if not v or v.passed:
        return []
    return [i for i in v.issues if _target_of(i) in (target, None)]


def _target_of(issue: VerificationIssue) -> str | None:
    if issue.where.startswith("cv"):
        return "cv"
    if issue.where.startswith("cover_letter"):
        return "letter"
    return None  # unknown location: both documents get the feedback


def _generation_prompt(state: AgentState, target: str) -> str:
    posting, fit = state["posting"], state["fit"]
    parts = [
        f"JOB:\n{fence(posting.model_dump_json(indent=1))}",
        f"FIT:\n{fit.model_dump_json(indent=1)}",
        f"PROFILE:\n{_profile_json()}",
        _context(state),
    ]
    if issues := _issues_for(state, target):
        listed = "\n".join(f"- {i.where}: {i.reason} ({i.text})" for i in issues)
        parts.append(f"Fix these verifier issues:\n{listed}")
    if notes := state.get("edit_notes"):
        parts.append(f"Candidate change request (apply it within the hard rules): {notes}")
    return "\n\n".join(p for p in parts if p)


def tailor_cv(state: AgentState) -> dict:
    cv = structured(
        TailoredCV,
        system=prompts.TAILOR.format(language=state["posting"].language.value),
        user=_generation_prompt(state, "cv"),
        step="tailor_cv",
    )
    return {"cv": cv}


def write_cover_letter(state: AgentState) -> dict:
    letter = structured(
        CoverLetter,
        system=prompts.COVER_LETTER.format(language=state["posting"].language.value),
        user=_generation_prompt(state, "letter"),
        step="cover_letter",
    )
    return {"cover_letter": letter}


# ---------- 4. Verification ----------


def verify(state: AgentState) -> dict:
    profile = load_profile()
    cv, letter = state["cv"], state.get("cover_letter")

    # Layer 1: deterministic, free, catches made-up IDs, misattribution, numbers and skills.
    issues = check_evidence_ids(profile, cv, letter, posting_text=state.get("posting_text", ""))

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

    targets = {_target_of(i) for i in issues}
    regenerate = BOTH if None in targets else [t for t in BOTH if t in targets]
    result = VerificationResult(passed=not issues, issues=issues)
    return {
        "verification": result,
        "verification_history": [result],
        "verify_attempts": state.get("verify_attempts", 0) + 1,
        "regenerate": regenerate,
    }


# ---------- 5. Approval + output ----------


def human_approval(state: AgentState) -> dict:
    request = ApprovalRequest(
        fit=state["fit"],
        cv=state["cv"],
        cover_letter=state.get("cover_letter"),
        verification=state["verification"],
    )
    answer = interrupt(request.model_dump(mode="json"))
    decision = ApprovalAnswer.model_validate(answer)
    if decision.approved:
        return {"status": "approved"}
    # Rejected with edit notes -> regenerate both documents with them.
    return {
        "edit_notes": decision.notes,
        "verification": None,
        "verify_attempts": 0,
        "regenerate": BOTH,
    }


def render_and_log(state: AgentState, config: RunnableConfig) -> dict:
    run_id = config["configurable"]["thread_id"]
    profile, posting = load_profile(), state["posting"]
    out_dir = run_output_dir(posting, run_id)
    cv_path = render_cv(profile, state["cv"], posting, out_dir)
    letter_path = None
    if letter := state.get("cover_letter"):
        letter_path = render_cover_letter(profile, letter, posting, out_dir)
    log_application(run_id, posting, state["fit"].score, cv_path, letter_path)
    update = {"cv_path": str(cv_path), "status": "done"}
    if letter_path:
        update["letter_path"] = str(letter_path)
    return update
