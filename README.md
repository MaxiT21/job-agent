# Job Application Agent

Paste a job posting → get a fit analysis, a tailored CV and a cover letter (both `.docx`).
Every sentence is traceable to the candidate's real experience, and nothing is sent without human approval.

> 🚧 Work in progress: backend, CLI and evals work end to end; web UI, deployment and published eval results are next.

## Why
Tailoring a CV per application takes ~30 min and it's tempting to stretch the truth.
This agent does the tailoring in about a minute and **cannot invent experience**:
it only selects, reorders and rewords items from a structured profile, and a verifier
checks every line against the evidence it cites.

## How it works

```
fetch → [unreadable?] ask to paste → extract requirements → [vague?] ask user
                             → match profile → fit score → [low fit?] ask user
                                             → tailor CV → cover letter → verify
                                               verify → [failed] regenerate only the failing document
                                                      → human approval → [edits] regenerate
                                                                       → render CV + letter .docx + log
```

- **Workflow where it's predictable, agent decisions where it isn't**: LangGraph conditional edges for unreadable URLs, vague postings, low fit, failed verification and user edits. Details and the generated graph diagram: [`docs/architecture.md`](docs/architecture.md).
- **Deterministic where possible**: the fit score and the first verification layer are plain code (tested), not LLM output.
- **Two-layer verification**:
  1. *Deterministic* (`scoring.py`, free, unit-tested): every line cites existing profile IDs; each CV bullet cites its own job/project and never borrows another one's evidence; every number appears in the cited evidence; skills exist in the profile; entries are real and unique.
  2. *LLM fact-check*: each line is checked against the evidence it cites (paraphrase OK, new facts not).
- **Untrusted input stays data**: the posting is fenced in tags it cannot close and prompts treat it as data; URL fetching blocks private/local addresses (SSRF) and oversized pages.
- **Provider-agnostic**: all LLM calls go through LiteLLM; cost and latency are recorded per step and per run.
- **Durable runs**: checkpoints in SQLite, so a run paused for your answer (or failed on a provider outage) can be resumed or retried later.

## Stack
LangGraph · FastAPI · Pydantic · LiteLLM · python-docx · SQLite · Docker · Next.js (planned) · Supabase (planned)

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

## CLI
The whole agent in the terminal, no frontend needed (same database as the API):
```bash
cd backend
uv run python -m app.cli run --url https://example.com/job   # or --file posting.txt / --text "..."
uv run python -m app.cli resume <run-id>                      # continue a paused or failed run
uv run python -m app.cli applications                         # tracker
```

## API
Interactive docs at `http://localhost:8000/docs`. Runs persist in SQLite (`backend/outputs/job_agent.db`), so they survive restarts.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/runs` | Start from `{"posting_url": ...}` or `{"posting_text": ...}` |
| `GET` | `/runs/{id}` | Current state: `status`, `waiting_for`, fit, CV, letter, verification, per-run LLM usage |
| `POST` | `/runs/{id}/resume` | Answer `waiting_for` with `{"value": {...}}` (shape depends on its `type`) |
| `POST` | `/runs/{id}/retry` | Re-run the step that failed (`status: "error"`, e.g. provider outage) |
| `GET` | `/runs/{id}/files/{cv\|cover_letter}` | Download the `.docx` |
| `GET` | `/applications` | Tracker: one row per approved run |
| `PATCH` | `/applications/{id}` | `{"status": "applied" \| "interview" \| "offer" \| "rejected" \| "withdrawn"}` |

`waiting_for.type` → expected answer:

| type | when | answer |
|---|---|---|
| `paste_text` | the URL could not be read | `{"text": "..."}` |
| `clarify` | the posting is too vague | `{"answer": "..."}` |
| `low_fit` | fit score below `LOW_FIT_THRESHOLD` | `{"proceed": true \| false}` |
| `approve` | documents ready for review | `{"approved": true}` or `{"approved": false, "notes": "..."}` |

## Evals
Extraction precision/recall, vague-posting detection, fit-score agreement with hand labels and, with `--full`, how often drafts pass verification and how many flagged lines survive retries, plus cost and latency per model. See [`evals/`](evals/). Results: _pending first run with a real API key._

## Design decisions
- No auto-submitting and no LinkedIn scraping (ToS). The agent prepares, the human sends.
- Real candidate data never enters the repo; a fictional sample profile is used instead.

## Development
```bash
cd backend
uv run pytest                                   # 85+ tests, no network, no LLM
uv run ruff check . ../evals && uv run ruff format . ../evals
uv run python -m app.agent.graph                # print the graph as Mermaid (docs/architecture.md)
```
CI runs lint and tests on every push and PR. Changes are logged in [`CHANGELOG.md`](CHANGELOG.md).

## Roadmap
- [x] Profile, extraction, matching, deterministic fit score
- [x] CV + cover letter, two-layer verifier with targeted retries, human approval, tracker
- [x] Persistent runs (SQLite), typed API, CLI, eval harness
- [ ] First eval results with a real model (Gemini) published here
- [ ] Next.js UI (run view with evidence table, tracker)
- [ ] Deploy (Vercel + Railway/Render), Postgres/Supabase for checkpoints + tracker, demo video
- [ ] Job discovery (Greenhouse/Lever/Ashby/InfoJobs APIs, weekly digest)

## License
[MIT](LICENSE)
