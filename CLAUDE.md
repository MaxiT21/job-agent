# Job Application Agent

AI agent that takes a job posting (URL or text) and produces a fit analysis, a tailored CV (.docx) and a cover letter. Portfolio project for AI developer roles.

## Core principle
The agent must NEVER invent experience. It only selects, reorders and rewords items from `backend/data/profile.yaml` (fallback: `profile.sample.yaml`). Every generated line carries `evidence_ids` pointing to profile IDs, and a two-layer verifier checks them (deterministic ID/skill check in `scoring.py` + LLM fact-check).

## Stack
- Backend: Python 3.12, FastAPI, Pydantic v2, LangGraph, LiteLLM (multi-provider), python-docx
- Frontend (planned): Next.js + TypeScript + Tailwind, deployed on Vercel
- Storage (planned): Supabase for the application tracker and the LangGraph checkpointer

## Structure
- `backend/app/schemas.py`: Pydantic contracts between all steps
- `backend/app/agent/graph.py`: LangGraph wiring (fetch → extract → match → tailor → cover letter → verify → human approval → render)
- `backend/app/agent/nodes.py`: graph nodes; `interrupt()` pauses for user input (vague posting, low fit, approval)
- `backend/app/agent/prompts.py`: all prompts
- `backend/app/scoring.py`: deterministic fit score + evidence checks (no LLM)
- `backend/app/llm.py`: single `structured()` LiteLLM wrapper, logs cost/latency per step
- `backend/app/main.py`: API (`POST /runs`, `POST /runs/{id}/resume`, `GET /runs/{id}/cv`)
- `evals/`: eval dataset + runner

## Conventions
- All LLM calls go through `llm.structured()` with a Pydantic schema. No raw string parsing.
- Keep anything that can be deterministic out of the LLM (scores, validation) and cover it with tests.
- Tests must not call an LLM: `cd backend && uv run pytest`.
- Lint/format before committing: `uv run ruff check . ../evals && uv run ruff format . ../evals`.
- Dependencies live in `backend/pyproject.toml` + `uv.lock` (`uv add <pkg>`); never edit the lockfile by hand.
- Keep docs current in the same commit as the change: README, CLAUDE.md, CHANGELOG (`Unreleased`), sub-READMEs.
- Never commit `backend/data/profile.yaml`, `.env` or `backend/outputs/` (real personal data).
- No auto-submitting applications and no LinkedIn scraping.

## Run
`.env` at the repo root (copy `.env.example`). Then `cd backend && uv sync && uv run uvicorn app.main:app --reload`.
