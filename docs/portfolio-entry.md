# Showing the project on the portfolio

The portfolio (`MaxiT21/portfolio`, https://maximotorassa.vercel.app) lists projects in
`src/content/projects.ts`. The public demo of this project is a separate Vercel deployment of
`frontend/` in demo mode; it allows being framed by the portfolio, so `embed: true` shows it
live inside the project's detail view.

## 1. Deploy the demo (once)

1. On Vercel: **Add New → Project → Import `MaxiT21/job-agent`**.
2. **Root Directory:** `frontend`. Framework preset: Next.js.
3. **Environment variable:** `NEXT_PUBLIC_DEMO` = `1` (nothing else: the demo has no backend and no keys).
4. Deploy. Pick a project name such as `job-agent-demo` → `https://job-agent-demo.vercel.app`.

Every push to `main` redeploys it. To refresh the recordings: `cd backend && uv run python -m scripts.record_demo`, commit `frontend/public/demo/`.

## 2. Add the entry to `src/content/projects.ts`

Replace the URL if you chose a different Vercel name. Drop a screenshot of the run page at
`public/projects/job-agent.png` in the portfolio and keep the `image` line, or remove it.

```ts
  {
    slug: "job-agent",
    title: "Job Application Agent",
    year: "2026",
    featured: true,
    accent: "#9c4530",
    status: "live",
    role: { en: "Personal project", es: "Proyecto personal" },
    tech: ["Python", "LangGraph", "FastAPI", "Next.js", "TypeScript", "Gemini"],
    tagline: {
      en: "An AI agent that tailors your CV — and can't invent experience",
      es: "Un agente de IA que adapta tu CV — sin poder inventar experiencia",
    },
    description: {
      en: "Paste a job posting and the agent extracts its requirements, scores your fit, and drafts a tailored CV and cover letter. Every sentence must cite an item of your real profile: a deterministic verifier and an LLM fact-checker reject anything unsupported and have it rewritten before you approve. It pauses to ask when a posting is vague or a poor fit, and nothing is created without your approval.",
      es: "Pegas una oferta y el agente extrae sus requisitos, puntúa tu encaje y redacta un CV y una carta adaptados. Cada frase debe citar un elemento de tu perfil real: un verificador determinista y un fact-checker con LLM rechazan lo que no está respaldado y lo hacen reescribir antes de que lo apruebes. Pregunta cuando la oferta es vaga o encaja poco, y no se genera nada sin tu aprobación.",
    },
    highlights: [
      {
        en: "Every CV line cites real profile evidence",
        es: "Cada línea del CV cita evidencia real del perfil",
      },
      {
        en: "Two-layer verifier: deterministic checks + LLM fact-check",
        es: "Verificador en dos capas: reglas deterministas + fact-check con LLM",
      },
      {
        en: "Human-in-the-loop LangGraph agent with durable, resumable runs",
        es: "Agente LangGraph con humano en el bucle y ejecuciones persistentes",
      },
      {
        en: "Evaluated on a labelled dataset: extraction, fit agreement, hallucinations",
        es: "Evaluado con un dataset etiquetado: extracción, encaje y alucinaciones",
      },
      {
        en: "Guided profile builder: the AI organises your own words, never adds",
        es: "Constructor de perfil guiado: la IA ordena tus palabras, nunca añade",
      },
    ],
    specs: [
      { value: "0 / 69", label: { en: "unsupported lines shipped (evals)", es: "líneas sin respaldo entregadas (evals)" } },
      { value: "7 / 7", label: { en: "fit scores matching hand labels", es: "encajes iguales a las etiquetas" } },
      { value: "2-layer", label: { en: "anti-hallucination verifier", es: "verificador anti-alucinación" } },
    ],
    image: "/projects/job-agent.png",
    url: "https://job-agent-demo.vercel.app",
    repo: "https://github.com/MaxiT21/job-agent",
    embed: true,
  },
```

The `specs` numbers come from `evals/` (Gemini Flash, 2026-11-15); update them when the evals
are re-run.
