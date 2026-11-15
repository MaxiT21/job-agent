# Web App + Portfolio Demo — Design

Status: draft for approval · 2026-11-15

## Intent

Máximo wants to use the job agent visually instead of from the terminal, and to show it on his portfolio (https://maximotorassa.vercel.app, repo `MaxiT21/portfolio`) as a project that recruiters can click through. It is a single-user tool: running the AI for strangers would cost money, so the public version replays recorded runs and makes no AI calls.

## Goals

1. **Private live app** (only Máximo, behind a password): start a run from a posting URL or text, answer the agent's questions, review fit / CV / cover letter / verifier results, approve or request edits, download the `.docx` files, track applications.
2. **Profile builder**: guided questions per section plus free text; the AI turns the answers into the structured profile (organises, never adds) and asks follow-up questions about gaps; Máximo reviews and edits before saving. This replaces hand-editing `profile.yaml`.
3. **Public demo**: the same screens replaying a few real recorded runs on the fictional sample profile; deployable to Vercel on its own (no backend, no keys, no AI calls), embeddable in the portfolio's project detail view.
4. Basic, clean UI now; prettier later. It should not look out of place next to the portfolio.

## Non-goals (for now)

- Multiple users, sign-up, public live runs, bring-your-own-key.
- Hosting the backend online (local first; the design keeps it possible).
- Polished visuals/animations, mobile-perfect layouts, Spanish UI.
- Importing a CV from PDF/.docx (pasting CV text into the builder covers it).
- Editing the portfolio repo (a ready-to-paste `projects.ts` entry is delivered instead; adding it is Máximo's call).

## Anti-goals (failure even if it works)

- An API key, the password, or Máximo's real profile reaching the browser bundle, the demo build or the git repo.
- The demo calling an AI model or showing real personal data.
- The profile builder inventing experience (same core principle as the agent).
- The UI hiding the evidence: the "every line is backed by a profile ID" story must be visible.

## Approaches considered

- **Website: Next.js app + existing FastAPI (chosen)** — matches the README plan and the portfolio stack, typed API already exists, deploys to Vercel. Costs a second process. Alternatives: FastAPI-served HTMX pages (one process, but clunky interactive screens, hard to polish), Streamlit/Gradio (fastest, generic look, fights the question flow, likely thrown away).
- **Showcase: replay demo (chosen)** + README video/GIF and eval table. Free and always online. Alternatives: live runs with a demo code (needs a hosted backend and quotas; later upgrade), bring-your-own-key (recruiters won't).

## Architecture

```
Browser ──> Next.js (frontend/) ──/api/* rewrite──> FastAPI (backend/) ──> LiteLLM ──> Gemini
                │                                        └─ SQLite: checkpoints, tracker, profile answers
                └─ demo build: reads frontend/demo/*.json, no backend
```

- **Same-origin proxy**: the browser only talks to Next.js; `next.config` rewrites `/api/*` to `BACKEND_URL` (server-side env). The session cookie is first-party, CORS is not needed, the backend URL never reaches the client.
- **One UI, two data sources**: every screen renders from the API's `RunView` / `Profile` / `Application` types. A small client interface (`AgentClient`) has two implementations: `HttpClient` (live) and `DemoClient` (recorded JSON). `NEXT_PUBLIC_DEMO=1` picks the demo at build time.
- **Types from the contract**: TypeScript types are generated from the backend's OpenAPI schema (`openapi-typescript`), committed, and CI fails if they are stale.

## Backend changes

1. **Auth (single user)**
   - `APP_PASSWORD` and `SESSION_SECRET` in `.env` (never committed). The backend refuses to serve protected endpoints if `APP_PASSWORD` is unset.
   - `POST /auth/login {password}` → constant-time compare → HttpOnly, SameSite=Lax cookie (`Secure` when not localhost) holding an HMAC-signed expiry (30 days). `POST /auth/logout`, `GET /auth/me`.
   - Every endpoint except `/health` and `/auth/*` requires the cookie (FastAPI dependency).
   - Login throttling: in-memory, per IP, exponential backoff after 5 failures.
2. **Background runs**
   - `POST /runs`, `/resume`, `/retry` return immediately (`202`, `status: "running"`); the graph runs in a worker thread via `graph.stream(..., stream_mode="updates")`.
   - `RunView` gains `step` (node currently running, for a progress line) — kept in memory per run.
   - One in-flight execution per run (lock); a second resume while running → `409`. This also fixes the deferred "concurrent resumes" minor.
   - A run interrupted by a server restart (pending node, no interrupt, no error, not in flight) shows `status: "error"` with a "server restarted" message and can be retried.
   - `GET /runs` lists recent runs (id, created, company/title once known, status) for the home page.
3. **Verification history**: state keeps every verification pass (`verification_history`), so the UI can show "the verifier caught X → regenerated → passed". This is the most convincing moment for the demo.
4. **Profile API**
   - `GET /profile/questions`: guided sections, each with a prompt and hints (what to include: dates, tools, team size, measurable results). Includes an optional "paste your current CV" field.
   - `GET /profile/answers`, `PUT /profile/answers`: saved answers (SQLite), so the builder can be resumed and extended.
   - `POST /profile/draft`: LLM structures the answers into a `Profile` (`structured()` with the `Profile` schema; IDs generated in code if missing/duplicated) plus `follow_up_questions` about gaps. A deterministic check flags numbers, organisations and dates in the draft that do not appear in the answers; flagged lines are shown to the user, not silently kept.
   - `GET /profile`, `PUT /profile`: read / validate + atomically write `data/profile.yaml`, clear the profile cache. Response says whether the real or the sample profile is active.
5. **Demo recording script** (`backend/scripts/record_demo.py`, run manually with a real key): runs the scenarios below on the sample profile, auto-answering questions, and writes for each scenario the ordered list of `RunView` snapshots (one per pause/finish) to `frontend/demo/<scenario>.json` and the `.docx` files to `frontend/public/demo/<scenario>/`. Scenarios: strong match; low fit ("apply anyway?"); vague posting (clarifying question); a run whose first draft the verifier rejected; one Spanish posting. The script refuses to run if the real profile would be loaded.

## Frontend (`frontend/`)

Next.js 16 (App Router), React 19, TypeScript, Tailwind 4, the portfolio's colour tokens and fonts (paper `#f4f1ec`, ink `#1a1a18`, terracotta `#9c4530`, Playfair / Inter / JetBrains Mono) for a consistent brand with minimal styling effort.

Pages:
- `/login` (live only): password field.
- `/` — **New application**: paste text or URL → start → go to the run. Below: recent runs. *Demo*: scenario cards instead of the form.
- `/runs/[id]` — **Run**: header (company, title, status, progress line while running), then by state:
  - `paste_text` / `clarify`: question + answer box.
  - `low_fit`: score, gap list, "Apply anyway" / "Stop".
  - `approve`: **evidence table** (requirement → met/partial/gap → evidence chips; hovering a chip shows the profile text it points to), CV preview, cover letter preview, verifier panel (history + remaining issues), "Approve" / "Request changes" (notes).
  - `done`: download buttons, summary. `error`: message + Retry.
  - always: usage (calls, time, cost).
- `/applications` — **Tracker**: table with a status dropdown.
- `/profile` — **Profile builder**: step through the guided sections (answers autosave) → "Build my profile" → review screen (editable items and bullets, flagged lines highlighted, follow-up questions to answer and rebuild) → Save. Shows whether the agent is currently using the real or sample profile.
- Demo mode: banner "Demo — recorded runs on a fictional candidate. No AI is called." Forms are read-only or step through the recording; downloads serve the recorded files.

Embedding: the demo build sends `Content-Security-Policy: frame-ancestors 'self' https://maximotorassa.vercel.app` so the portfolio can embed it; the live app sends `frame-ancestors 'none'`.

## Privacy & keys

- Keys and the password live only in the backend `.env` (gitignored, not in the Docker image); the frontend has no secrets. `BACKEND_URL` is server-side only.
- Real profile and answers live in `backend/data/` and the SQLite file (gitignored, Docker volume).
- The demo bundle contains only the fictional sample profile's recordings; the recorder refuses to run with the real profile; a test asserts demo fixtures contain the sample candidate's name and not the real one's.

## Testing

- Backend: pytest for auth (login, throttling, protected endpoints), background runs (202, progress, lock/409, restart recovery), profile API (draft with FakeLLM, invented-number flagging, save/validate), verification history. Still no network.
- Frontend: Vitest + Testing Library for the run screen in each state, the evidence table, the profile review, and `DemoClient` stepping; one Playwright smoke test that clicks through the demo build (no backend needed); generated API types up to date (CI check).
- CI: backend job (existing) + frontend job (lint, typecheck, unit tests, demo build, e2e smoke).

## Running

- Local: `docker compose up` (backend + frontend) or `uv run uvicorn …` + `npm run dev`. Set `APP_PASSWORD` and `SESSION_SECRET` in `.env`.
- Demo: Vercel project with root `frontend/`, env `NEXT_PUBLIC_DEMO=1` (deployment needs Máximo's Vercel login; the portfolio entry is a separate step).

## Known limitations (accepted)

- Runs read the current profile. Saving a new profile while a run is paused may make that run's evidence IDs stale; the profile page warns when runs are waiting, and the verifier would flag unknown IDs anyway.
- Background runs live in the API process (thread pool). Fine for one user; a job queue is only needed if this ever becomes multi-user.

## Left to the builder

Component structure, exact copy of guided questions, polling interval (1–2 s while running), table/editor details, icons, and how the demo steps through snapshots (auto-advance vs "next" button) — any reasonable choice.
