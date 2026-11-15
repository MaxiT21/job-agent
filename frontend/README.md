# Frontend (Next.js) — week 3

Create it with:
```bash
npx create-next-app@latest . --typescript --tailwind --app
```

## Pages
1. **New application** (`/`): textarea for the posting (or URL) → `POST /runs`
2. **Run view** (`/runs/[id]`): renders whatever the agent is waiting for (`waiting_for.type`):
   - `clarify` → show the question + answer box → `POST /runs/{id}/resume` with `{ "answer": "..." }`
   - `low_fit` → score, gaps, "Apply anyway?" → resume with `{ "proceed": true|false }`
   - `approve` → fit table (requirement → status → evidence), CV preview, cover letter,
     verifier issues → resume with `{ "approved": true }` or `{ "approved": false, "notes": "..." }`
   - done → download button (`GET /runs/{id}/cv`)
3. **Tracker** (`/applications`): table from Supabase (week 3)

## Tip
The fit table with evidence links is the screenshot for your README and demo video:
it makes the "no hallucination" design visible at a glance.
