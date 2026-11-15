// Typed against the generated API types: if the backend contract changes, these stop compiling.
import type { Profile, RunView, VerificationResult } from "@/lib/types";

export const profile: Profile = {
  name: "Alex Example",
  email: "alex.example@example.com",
  location: "Barcelona, Spain",
  links: { github: "github.com/alex-example" },
  summary: "Computer engineering student.",
  items: [
    {
      id: "exp-consulting",
      kind: "experience",
      title: "Technical Consultant Intern",
      org: "Example Consulting",
      period: "Feb 2026 - Jul 2026",
      bullets: [
        {
          id: "exp-consulting-b2",
          text: "Tracked and triaged defects in Jira and validated data with SQL queries.",
          tags: [],
        },
      ],
      tags: ["sql"],
    },
    {
      id: "proj-network-monitor",
      kind: "project",
      title: "Home Network Monitor",
      bullets: [
        {
          id: "proj-network-monitor-b1",
          text: "Built a FastAPI backend that scans the local network.",
          tags: [],
        },
      ],
      tags: ["python", "fastapi"],
    },
    { id: "skills-core", kind: "skill", title: "Core skills", bullets: [], tags: ["python", "sql"] },
  ],
};

const failed: VerificationResult = {
  passed: false,
  issues: [
    {
      where: "cover_letter[1]",
      text: "I led a team of 5 testers.",
      reason: "Number not in evidence: 5",
    },
  ],
};
const passed: VerificationResult = { passed: true, issues: [] };

const fit = {
  score: 80,
  summary: "Strong backend match; Kubernetes is a gap.",
  matches: [
    { requirement_id: "r1", status: "met" as const, evidence_ids: ["proj-network-monitor-b1"], note: "FastAPI backend" },
    { requirement_id: "r2", status: "partial" as const, evidence_ids: ["exp-consulting-b2"], note: "SQL in QA work" },
    { requirement_id: "r3", status: "gap" as const, evidence_ids: [], note: "No Kubernetes" },
  ],
};

const cv = {
  summary: { text: "Engineering student building Python backends.", evidence_ids: ["skills-core"] },
  entries: [
    {
      item_id: "proj-network-monitor",
      bullets: [{ text: "Built a FastAPI backend.", evidence_ids: ["proj-network-monitor-b1"] }],
    },
    {
      item_id: "exp-consulting",
      bullets: [{ text: "Validated data with SQL.", evidence_ids: ["exp-consulting-b2"] }],
    },
  ],
  skills: ["Python", "SQL"],
};

const letter = {
  paragraphs: [
    { text: "Your platform team builds with FastAPI, like I did.", evidence_ids: ["proj-network-monitor-b1"] },
    { text: "I validated data with SQL during my internship.", evidence_ids: ["exp-consulting-b2"] },
  ],
};

export function run(overrides: Partial<RunView> = {}): RunView {
  return {
    run_id: "r1",
    created_at: "2026-11-15T10:00:00Z",
    status: "waiting",
    step: null,
    error: null,
    posting: {
      title: "Backend Developer Intern",
      company: "Acme",
      location: "Barcelona",
      seniority: "intern",
      language: "en",
      is_vague: false,
      clarifying_question: null,
      responsibilities: [],
      requirements: [
        { id: "r1", text: "Python and FastAPI", category: "skill", importance: "must" },
        { id: "r2", text: "SQL", category: "skill", importance: "must" },
        { id: "r3", text: "Kubernetes", category: "skill", importance: "nice" },
      ],
    },
    fit,
    cv,
    cover_letter: letter,
    verification: passed,
    verification_history: [failed, passed],
    waiting_for: { type: "approve", fit, cv, cover_letter: letter, verification: passed },
    files: { cv: false, cover_letter: false },
    usage: {
      calls: [
        { step: "extract", model: "gemini/x", latency_s: 7.4, cost_usd: 0.002, ok: true },
        { step: "match", model: "gemini/x", latency_s: 16.7, cost_usd: 0.008, ok: true },
      ],
      total_cost_usd: 0.01,
      total_latency_s: 24.1,
    },
    ...overrides,
  };
}
