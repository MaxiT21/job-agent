# Frontend (Next.js)

The web app for the job agent. One codebase, two builds:

| Build | Command | What it is |
|---|---|---|
| **Private app** | `npm run dev` / `npm run build` | Talks to the FastAPI backend through `/api/*` (proxied by Next.js, so the session cookie is first-party and the backend URL never reaches the browser). Behind `APP_PASSWORD`. |
| **Public demo** | `npm run build:demo` | No backend, no keys, no AI calls: replays runs recorded on the fictional sample profile. Can be embedded by the portfolio. |

## Develop
```bash
# terminal 1 (repo root .env needs GEMINI_API_KEY, APP_PASSWORD)
cd backend && uv run uvicorn app.main:app --reload
# terminal 2
cd frontend && npm install && npm run dev      # http://localhost:3000
```
`BACKEND_URL` (server-side only) overrides the backend address, default `http://localhost:8000`.

## Checks
```bash
npm run lint && npm run typecheck && npm test   # unit tests, no backend needed
npm run build:demo && npm run e2e               # demo smoke test (Playwright)
```

## API types
`src/lib/api-types.ts` is generated from `openapi.json`, which the backend exports:
```bash
cd backend && uv run python -m scripts.export_openapi   # a backend test fails if it is stale
cd frontend && npm run gen:types                         # CI fails if this is stale
```
Use the aliases in `src/lib/types.ts`; never edit `api-types.ts` by hand.

## Structure
- `src/lib/client.ts` — `AgentClient`: everything the screens need. `HttpClient` (live) and `DemoClient` (recordings) implement it; `getAgent()` picks one per build.
- `src/app/` — pages; `src/components/` — UI.
