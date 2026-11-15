# Job Application Agent

Paste a job posting → get a fit analysis, a tailored CV (.docx) and a cover letter.
Every sentence is traceable to the candidate's real experience, and nothing is sent without human approval.

> 🚧 Work in progress. Demo link, eval results and video coming in week 4.

## Why
Tailoring a CV per application takes ~30 min and it's tempting to stretch the truth.
This agent does the tailoring in about a minute and **cannot invent experience**:
it only selects, reorders and rewords items from a structured profile, and a verifier
checks every line against the evidence it cites.

## How it works

```
fetch → extract requirements → [vague?] ask user
                             → match profile → fit score → [low fit?] ask user
                                             → tailor CV → cover letter → verify
                                               verify → [failed] retry with feedback
                                                      → human approval → [edits] regenerate
                                                                       → render .docx + log
```

- **Workflow where it's predictable, agent decisions where it isn't**: LangGraph conditional edges for vague postings, low fit, failed verification and user edits.
- **Deterministic where possible**: the fit score and the first verification layer are plain code (tested), not LLM output.
- **Two-layer verification**: (1) every line must cite existing profile IDs, skills must exist in the profile; (2) an LLM fact-check of each line against the evidence it cites.
- **Provider-agnostic**: all LLM calls go through LiteLLM; cost and latency are logged per step.

## Stack
LangGraph · FastAPI · Pydantic · LiteLLM · python-docx · Next.js · Supabase (planned) · Docker

## Run locally
Requires [uv](https://docs.astral.sh/uv/) (it installs Python 3.12 for you).

```bash
cp .env.example .env           # repo root: set MODEL and the provider key
cd backend
uv sync                        # creates .venv from the lockfile
uv run pytest                  # no LLM calls needed
uv run uvicorn app.main:app --reload   # http://localhost:8000/docs
```

Use your own profile: copy `backend/data/profile.sample.yaml` to `backend/data/profile.yaml` (gitignored) and fill it in.

Or with Docker: `docker compose up --build` (reads the same root `.env`; your profile is mounted, never baked into the image).

## Evals
_Coming soon_: extraction precision/recall, hallucination rate, fit-score agreement with human judgement, cost and latency per provider. See [`evals/`](evals/).

## Design decisions
- No auto-submitting and no LinkedIn scraping (ToS). The agent prepares, the human sends.
- Real candidate data never enters the repo; a fictional sample profile is used instead.

## Roadmap
- [ ] Week 1: profile, extraction, matching, fit score (CLI)
- [ ] Week 2: CV + cover letter, verifier loop, approval, tracker
- [ ] Week 3: Next.js UI, Supabase tracker + checkpointer
- [ ] Week 4: evals, deploy (Vercel + Railway/Render), demo video
- [ ] Week 5: job discovery (Greenhouse/Lever/Ashby/InfoJobs APIs, weekly digest)
