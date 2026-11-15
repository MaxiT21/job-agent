# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Offline graph test harness (`tests/fakes.py`): a scripted LLM drives the full pipeline, including interrupts, retries and edits.

### Changed
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
