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

### Changed
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
