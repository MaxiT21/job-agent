# Job Application Agent

Paste a job posting → get a fit analysis, a tailored CV and a cover letter (both `.docx`).
Every sentence is traceable to the candidate's real experience, and nothing is sent without human approval.

**Live demo: [job-agent-demo-ten.vercel.app](https://job-agent-demo-ten.vercel.app)** — replays real runs of the agent on a fictional candidate (no sign-up, no AI calls). Also on [my portfolio](https://maximotorassa.vercel.app).

![Demo walkthrough: pick a recorded run, watch the agent work, hover an evidence ID to see the profile text behind it, see the fact-check that caught and fixed a claim, approve and download](docs/screenshots/demo.gif)

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
LangGraph · FastAPI · Pydantic · LiteLLM (Gemini) · python-docx · SQLite · Next.js 16 · React 19 · TypeScript · Tailwind · Vitest · Playwright · Docker

## Run locally
Requires [uv](https://docs.astral.sh/uv/) (installs Python 3.12 for you) and Node 22+.

```bash
cp .env.example .env     # repo root: GEMINI_API_KEY, APP_PASSWORD (and SESSION_SECRET)

# terminal 1 — API
cd backend && uv sync && uv run uvicorn app.main:app --reload    # http://localhost:8000/docs

# terminal 2 — web app
cd frontend && npm install && npm run dev                         # http://localhost:3000
```
Log in with `APP_PASSWORD`. Then build your profile on the **Profile** page (guided questions → AI draft → review → save) and start an application on **New application**. Your profile, answers and runs stay on your machine (`backend/data/`, `backend/outputs/`, both gitignored).

Or with Docker: `docker compose up --build` → http://localhost:3000 (reads the same root `.env`; your profile is mounted, never baked into an image; the API is only reachable by the web app).

## Web app
| Page | What you do there |
|---|---|
| **New application** | Paste a posting or a URL; see recent runs |
| **Run** | Watch progress, answer the agent's questions, review fit + evidence (hover an ID to see your own words), CV and letter previews, fact-check history; approve or request changes; download the `.docx` files |
| **Applications** | Tracker with a status per application |
| **Profile** | Guided questions; the AI organises your answers, flags anything it couldn't find in them and asks follow-up questions; you edit and save |

The **public demo** is the same app built with `NEXT_PUBLIC_DEMO=1`: no backend, it replays runs recorded with the real agent (`backend/scripts/record_demo.py`). See [`frontend/README.md`](frontend/README.md) and [`docs/portfolio-entry.md`](docs/portfolio-entry.md).

## CLI
The whole agent in the terminal (same database as the API):
```bash
cd backend
uv run python -m app.cli run --url https://example.com/job   # or --file posting.txt / --text "..."
uv run python -m app.cli resume <run-id>                      # continue a paused or failed run
uv run python -m app.cli applications                         # tracker
```

## API
Interactive docs at `http://localhost:8000/docs`. Starting, answering and retrying return immediately; poll `GET /runs/{id}` while `status` is `running` (`409` if you answer a run that is still working). Everything except `/health` and `/auth/*` requires logging in with `APP_PASSWORD` (`POST /auth/login`), which sets an HttpOnly session cookie. Runs persist in SQLite (`backend/outputs/job_agent.db`), so they survive restarts.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/runs` | Recent runs (status, company, title, fit score) |
| `POST` | `/runs` | Start from `{"posting_url": ...}` or `{"posting_text": ...}` → `202`, runs in the background |
| `GET` | `/runs/{id}` | Current state: `status` (`running` + `step` while working), `waiting_for`, fit, CV, letter, verification, per-run LLM usage |
| `POST` | `/runs/{id}/resume` | Answer `waiting_for` with `{"value": {...}}` (shape depends on its `type`) → `202` |
| `POST` | `/runs/{id}/retry` | Re-run a step that failed (`status: "error"`, e.g. provider outage) or was interrupted by a restart → `202` |
| `GET` | `/runs/{id}/files/{cv\|cover_letter}` | Download the `.docx` |
| `GET` / `PUT` | `/profile` | The profile the agent uses (`source`: `custom` or `sample`) |
| `GET` | `/profile/questions` | Guided sections for the profile builder |
| `GET` / `PUT` | `/profile/answers` | Your saved answers |
| `POST` | `/profile/draft` | AI organises the answers into a profile draft + flags + follow-up questions (nothing saved) |
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
8 hand-labelled fictional postings (English, Spanish, Catalan) against the sample profile, run with `gemini/gemini-flash-latest` on 2026-11-15 (`--full`: extraction, matching, generation and verification). See [`evals/`](evals/) and [`evals/results/`](evals/results/).

| | Before prompt fixes | After |
|---|---|---|
| Extraction precision / recall | 0.89 / 0.95 | 0.91 / 0.98 |
| Vague posting detected | 8 / 8 | 8 / 8 |
| Fit score matches hand label | 7 / 7 | 7 / 7 |
| **Unsupported lines in final documents** | **0 / 70** | **0 / 69** |
| First draft passes verification | 1 / 7 | **6 / 7** |
| Verification passes per application | 2.29 | 1.14 |
| AI calls / cost for the whole eval | 63 / $0.44 | 52 / $0.28 |

How the fix was found: the verification history showed every first-pass failure came from the prompts asking for things the verifier must reject (invented "learning plans" for gaps, unverifiable "I haven't used X" sentences, and a profile summary that had no citable ID). Fixing the prompts, not loosening the verifier, made runs ~36% cheaper with the same zero unsupported lines.

### Model comparison (2026-11-17)
Same 8 postings, same prompts, `--full`, one run per model:

| Model | Extraction P / R | Fit matches label | First draft passes | **Unsupported lines left for review** | Cost | Avg latency / call |
|---|---|---|---|---|---|---|
| `gemini-3.1-flash-lite` | 1.00 / 1.00 | 6 / 7 | 0 / 7 | **7 / 59** | $0.06 | 1.5 s |
| `gemini-flash-latest` (default) | 0.91 / 0.98 | 7 / 7 | 2 / 7 | **0 / 67** | $0.38 | 11.6 s |
| `gemini-3.5-flash` | 0.89 / 0.95 | 7 / 7 | 6 / 7 | **0 / 67** | $0.32 | 7.7 s |
| `gemini-3.1-pro-preview` ¹ | 0.90 / 1.00 | 6 / 6 | 2 / 5 | **3 / 47** | $1.45 | 14.1 s |

¹ Partial: 5 of 8 postings (the API credits ran out mid-run).

What it shows:
- **The verifier is what makes cheap models usable, but not cheap enough.** Flash-Lite extracts requirements perfectly at a sixth of the cost, but none of its first drafts passed and 7 lines were still unsupported after the retries; they reach the approval screen flagged, never silently. Flash-class models leave none.
- **Bigger isn't better here.** Pro cost ~4× more, was the slowest, and still left 3 flagged lines in 5 postings: following "cite only what the evidence says" matters more than raw capability.
- **First-draft pass rate is noisy on 7 cases.** The default model passed 6/7 on 2026-11-15 and 2/7 on this run with identical prompts; the number to trust is the one that held in every Flash run, zero unsupported lines in the final documents. Next step: repeated runs per model to report a spread instead of a single number.

## Design decisions
- No auto-submitting and no LinkedIn scraping (ToS). The agent prepares, the human sends.
- Real candidate data never enters the repo; a fictional sample profile is used instead.

## Development
```bash
cd backend && uv run pytest && uv run ruff check . ../evals && uv run ruff format . ../evals
cd frontend && npm run lint && npm run typecheck && npm test
cd frontend && npm run build:demo && npm run e2e      # demo smoke test (Playwright)
cd backend && uv run python -m app.agent.graph        # graph as Mermaid (docs/architecture.md)
```
No test calls an LLM or needs the backend running. CI runs all of the above on every push and PR; a separate [eval gate](evals/README.md#regression-gate-ci) runs real model calls when prompts or the agent change. Changes are logged in [`CHANGELOG.md`](CHANGELOG.md).

## Roadmap
- [x] Profile, extraction, matching, deterministic fit score
- [x] CV + cover letter, two-layer verifier with targeted retries, human approval, tracker
- [x] Persistent runs (SQLite), typed API, CLI, eval harness, first Gemini eval results
- [x] Web app (password-protected) with profile builder; public demo of recorded runs
- [x] Demo on Vercel + portfolio entry
- [x] Demo GIF
- [x] Prompt fixes found via verification history: first drafts pass 6/7 (was 1/7)
- [x] Model comparison across Gemini tiers; eval regression gate in CI
- [ ] Hosted private app (Postgres/Supabase for checkpoints + tracker)
- [ ] Job discovery (Greenhouse/Lever/Ashby/InfoJobs APIs, weekly digest)

## License
[MIT](LICENSE)
