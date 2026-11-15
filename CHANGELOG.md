# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed
- Dependencies are managed with uv (`backend/pyproject.toml` + `backend/uv.lock`); `requirements.txt` removed.
- CI runs `ruff check`, `ruff format --check` and `pytest` against the locked environment.
- Docker image installs from the lockfile and runs as a non-root user.
- `.env` is read from the repo root (shared with docker compose); `backend/.env` overrides it.

### Fixed
- Provider API keys in `.env` are now exported to the process environment; previously LiteLLM never saw them.

### Security
- `.dockerignore` keeps `data/profile.yaml`, `.env` and `outputs/` out of the Docker image.

## [0.1.0] - 2026-11-15
- Initial scaffold: LangGraph pipeline, FastAPI endpoints, deterministic fit score and evidence check, `.docx` CV rendering.
