# Frontend (Next.js) — planned

Create it with:
```bash
npx create-next-app@latest . --typescript --tailwind --app
```
Generate API types from the backend's OpenAPI schema (`http://localhost:8000/openapi.json`) instead of writing them by hand.

## Pages
1. **New application** (`/`): textarea for the posting (or URL) → `POST /runs`
2. **Run view** (`/runs/[id]`): renders `status` and whatever the agent is waiting for (`waiting_for.type`):
   - `paste_text` → explain why the URL failed + textarea → `POST /runs/{id}/resume` with `{ "value": { "text": "..." } }`
   - `clarify` → show the question + answer box → resume with `{ "value": { "answer": "..." } }`
   - `low_fit` → score, gaps, "Apply anyway?" → resume with `{ "value": { "proceed": true|false } }`
   - `approve` → fit table (requirement → status → evidence), CV preview, cover letter,
     verifier issues → resume with `{ "value": { "approved": true } }` or `{ "value": { "approved": false, "notes": "..." } }`
   - `status: "error"` → show `error` + retry button (`POST /runs/{id}/retry`)
   - `status: "done"` → download buttons (`GET /runs/{id}/files/cv`, `/files/cover_letter`)
   - always: per-run cost/latency from `usage`
3. **Tracker** (`/applications`): table from `GET /applications`, status dropdown → `PATCH /applications/{id}`

## Tip
The fit table with evidence links is the screenshot for your README and demo video:
it makes the "no hallucination" design visible at a glance.
