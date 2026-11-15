# Job Application Agent

AI agent that takes a job posting (URL or text) and produces a fit analysis, a tailored CV and a cover letter (.docx). Portfolio project for AI developer roles.

## Core principle
The agent must NEVER invent experience. It only selects, reorders and rewords items from `backend/data/profile.yaml` (fallback: `profile.sample.yaml`). Every generated line carries `evidence_ids` pointing to profile IDs, and a two-layer verifier checks them (deterministic checks in `scoring.py`: IDs, ownership, numbers, skills + LLM fact-check).

## Stack
- Backend: Python 3.12, FastAPI, Pydantic v2, LangGraph, LiteLLM (multi-provider), python-docx
- Frontend: Next.js 16 + React 19 + TypeScript + Tailwind 4 (`frontend/`); private app (proxied to the backend) and public demo build (`NEXT_PUBLIC_DEMO=1`, recorded runs)
- Storage: SQLite (checkpoints + tracker) locally; Supabase/Postgres planned for deployment

## Structure
- `backend/app/schemas.py`: Pydantic contracts between all steps, incl. interrupt requests/answers
- `backend/app/agent/graph.py`: LangGraph wiring (fetch → extract → match → tailor → cover letter → verify → human approval → render); `tracked()` stores per-run LLM usage; `get_graph()` = SQLite-checkpointed graph
- `backend/app/agent/nodes.py`: graph nodes; `interrupt()` pauses for the user (unreadable URL, vague posting, low fit, approval)
- `backend/app/agent/prompts.py`: all prompts; `fence()` wraps untrusted posting text
- `backend/app/scoring.py`: deterministic fit score + layer-1 verifier (no LLM)
- `backend/app/llm.py`: single `structured()` LiteLLM wrapper; `track_usage()` collects calls
- `backend/app/profile_builder.py`: guided questions, saved answers, AI profile draft (IDs in code, unsupported facts flagged)
- `backend/app/fetch.py`: SSRF-safe posting fetch
- `backend/app/render/`: `.docx` CV and cover letter, one folder per run
- `backend/app/tracker.py`, `backend/app/db.py`: SQLite application tracker (same DB as checkpoints)
- `backend/app/auth.py`: single-user password auth (session cookie); private routes live on the `private` router in `main.py`
- `backend/app/runs.py`: run lifecycle (start/view/answer/retry/list), inline or on an executor; shared by API (background) and CLI (inline)
- `backend/app/main.py` + `app/api/models.py`: HTTP API (see README "API")
- `backend/app/cli.py`: interactive terminal runner
- `backend/tests/fakes.py`: `FakeLLM` + canned outputs valid against the sample profile
- `frontend/src/lib/client.ts`: `AgentClient` interface (HttpClient live / DemoClient recordings); `api-types.ts` is generated from `frontend/openapi.json`
- `evals/`: eval dataset + runner
- `docs/architecture.md`: pipeline, state, verification layers, persistence
- `docs/plans/`: implementation plans

## Conventions
- All LLM calls go through `llm.structured()` with a Pydantic schema. No raw string parsing.
- Keep anything that can be deterministic out of the LLM (scores, validation) and cover it with tests.
- Tests must not call an LLM: `cd backend && uv run pytest`. Drive graph/API tests with the `fake_llm` fixture.
- Every interrupt has a `*Request` model (what the agent asks) and a `*Answer` model (registered in `ANSWER_MODELS`).
- Lint/format before committing: `uv run ruff check . ../evals && uv run ruff format . ../evals`.
- Dependencies live in `backend/pyproject.toml` + `uv.lock` (`uv add <pkg>`); never edit the lockfile by hand.
- Keep docs current in the same commit as the change: README, CLAUDE.md, CHANGELOG (`Unreleased`), `docs/architecture.md`, sub-READMEs.
- After changing the graph, regenerate its diagram into `docs/architecture.md` (`uv run python -m app.agent.graph`); `tests/test_docs.py` fails if it is stale.
- Conditional edges must declare their targets (path map) so the graph stays inspectable.
- Never commit `backend/data/profile.yaml`, `.env` or `backend/outputs/` (real personal data).
- No auto-submitting applications and no LinkedIn scraping.

## Frontend conventions
- Read `frontend/AGENTS.md`: Next.js 16 differs from older versions; check `frontend/node_modules/next/dist/docs/` before using an API.
- After changing an API model: `cd backend && uv run python -m scripts.export_openapi`, then `cd frontend && npm run gen:types` (both are checked by tests/CI).
- Frontend checks: `npm run lint && npm run typecheck && npm test`.
- No secrets in the frontend: it only knows `BACKEND_URL` (server-side) and `NEXT_PUBLIC_DEMO`.

## Run
`.env` at the repo root (copy `.env.example`). Then `cd backend && uv sync && uv run uvicorn app.main:app --reload`.
