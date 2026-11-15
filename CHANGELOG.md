# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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

### Changed
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
- Interrupt answers are validated (`ClarifyAnswer`, `LowFitAnswer`, `ApprovalAnswer`); a plain-string answer no longer crashes the run, and "apply anyway" on a low-fit posting now actually continues (`{"proceed": true}`).
- Clarifications about the posting are kept for the whole run instead of being overwritten by later edit requests.
- Provider API keys in `.env` are now exported to the process environment; previously LiteLLM never saw them.

### Security
- `.dockerignore` keeps `data/profile.yaml`, `.env` and `outputs/` out of the Docker image.

## [0.1.0] - 2026-11-15
- Initial scaffold: LangGraph pipeline, FastAPI endpoints, deterministic fit score and evidence check, `.docx` CV rendering.
