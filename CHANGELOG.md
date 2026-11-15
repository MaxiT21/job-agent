# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added (web app)
- `frontend/`: Next.js 16 app scaffold with the portfolio's palette and fonts, `/api/*` proxy to the backend, CSP `frame-ancestors` (demo embeddable by the portfolio, private app never), TypeScript API types generated from the backend's OpenAPI schema (`frontend/openapi.json`, checked by a backend test and CI), Vitest, and a frontend CI job.
- Profile builder API: guided questions (`GET /profile/questions`), saved answers (`GET|PUT /profile/answers`), AI draft (`POST /profile/draft`: the model organises the answers, IDs are assigned in code, numbers and organisations not found in the answers are flagged, plus follow-up questions), and `GET|PUT /profile` (validated, written atomically, used by the agent immediately).
- Every verifier pass is kept (`verification_history` in state and `RunView`), so the UI can show what was caught and fixed.
- Background runs: `POST /runs`, `/resume`, `/retry` return `202` and the run continues in a worker thread; `RunView.step` reports the node in progress; answering a run that is still working returns `409`; runs left mid-pipeline by a server restart show as `error` and can be retried.
- `GET /runs` lists recent runs (company, title, status, fit score).
- Single-user auth: `APP_PASSWORD` → HMAC-signed HttpOnly session cookie (`/auth/login`, `/auth/logout`, `/auth/me`); login attempts throttled per IP after 5 failures; private endpoints return 401 without a session and 503 if no password is configured.

### Added
- Offline graph test harness (`tests/fakes.py`): a scripted LLM drives the full pipeline, including interrupts, retries and edits.

- Verifier layer 1 now also rejects: bullets that borrow evidence from a different job/project (misattribution), bullets that don't cite their own item, numbers not present in the cited evidence, skill/language items used as CV entries, and duplicate entries.
- Profile loading fails fast on duplicate IDs.

- Targeted regeneration: when verification fails, only the document with issues (CV or cover letter) is regenerated, and each gets only its own issues as feedback.
- Per-run LLM usage: every call (step, model, latency, cost) is stored in the run's state (`llm_calls`).
- Safe URL fetching (`app/fetch.py`): http(s) only, every redirect hop must resolve to a public IP, 2 MB / 15 s limits, JS-only pages rejected with a hint to paste the text.

- The cover letter is rendered to `.docx` too (greeting and sign-off in the posting's language are added by the renderer, not the LLM).
- Each run writes to its own folder (`outputs/runs/<date>_<company>_<title>_<run-id>/cv.docx`, `cover_letter.docx`), so repeated postings never overwrite earlier files.

- Runs persist in SQLite (LangGraph `SqliteSaver`), so they survive restarts; the application tracker lives in the same database with a status pipeline (`ready → applied → interview → offer / rejected / withdrawn`).
- API: typed responses (`RunView`, discriminated `waiting_for`), `POST /runs/{id}/retry` for failed steps, `GET /runs/{id}/files/{cv|cover_letter}`, `GET /applications`, `PATCH /applications/{id}`; `/health` reports whether the real or sample profile is loaded.
- If a posting URL can't be read, the run pauses with `paste_text` instead of failing.

- Interactive CLI (`python -m app.cli run|resume|applications`) sharing the run service and database with the API.

- Eval harness: 8 labelled fictional postings (en/es/ca), extraction P/R, vague detection, fit agreement, and `--full` verification metrics; results saved to `evals/results/`.

- `docs/architecture.md` with the graph diagram generated from code; a test fails if it goes stale.

### Changed
- Conditional edges declare their targets, so the graph can be drawn and inspected (e.g. LangGraph Studio).
- `.env.example` defaults to Gemini and documents every setting.
- A posting that is still vague after 2 clarifying answers (`MAX_CLARIFICATIONS`) moves on to the low-fit check instead of asking forever.
- A failing step no longer returns HTTP 500: the run is kept with `status: "error"` and can be retried.
- Resume answers are validated against the pending question (422 on the wrong shape, 409 if nothing is pending).
- `GET /runs/{id}/cv` replaced by `GET /runs/{id}/files/cv`; the CSV tracker replaced by SQLite.
- The posting is fenced in `<job_posting>` tags it cannot close, and every prompt treats it as untrusted data (prompt-injection guard).
- The LLM fact-checker reports issue locations in a fixed format so they can be routed.
- Dependencies are managed with uv (`backend/pyproject.toml` + `backend/uv.lock`); `requirements.txt` removed.
- CI runs `ruff check`, `ruff format --check` and `pytest` against the locked environment.
- Docker image installs from the lockfile and runs as a non-root user.
- `.env` is read from the repo root (shared with docker compose); `backend/.env` overrides it.

### Fixed
- LLM calls no longer force `temperature=0` (Gemini 3 can loop forever below 1.0; a profile draft hung for minutes). Temperature is now optional (`LLM_TEMPERATURE`), every call has a timeout (`LLM_TIMEOUT_S`, 120 s) and retries transient provider errors (`LLM_NUM_RETRIES`, 2).
- The CV/letter contact line skips empty fields instead of printing stray separators.
- LLM calls are recorded in every enclosing `track_usage()` block, so the eval runner's cost and call totals include calls made inside the graph.
- Interrupt answers are validated (`ClarifyAnswer`, `LowFitAnswer`, `ApprovalAnswer`); a plain-string answer no longer crashes the run, and "apply anyway" on a low-fit posting now actually continues (`{"proceed": true}`).
- Clarifications about the posting are kept for the whole run instead of being overwritten by later edit requests.
- Provider API keys in `.env` are now exported to the process environment; previously LiteLLM never saw them.

### Security
- `.dockerignore` keeps `data/profile.yaml`, `.env` and `outputs/` out of the Docker image.

## [0.1.0] - 2026-11-15
- Initial scaffold: LangGraph pipeline, FastAPI endpoints, deterministic fit score and evidence check, `.docx` CV rendering.
