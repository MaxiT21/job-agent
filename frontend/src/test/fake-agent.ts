import { vi } from "vitest";

import type { AgentClient } from "@/lib/client";

/** An AgentClient whose methods are all vi.fn(); override what a test needs. */
export function fakeAgent(overrides: Partial<AgentClient> = {}): AgentClient {
  const base: AgentClient = {
    demo: false,
    me: vi.fn().mockResolvedValue(true),
    login: vi.fn().mockResolvedValue(undefined),
    logout: vi.fn().mockResolvedValue(undefined),
    listRuns: vi.fn().mockResolvedValue([]),
    startRun: vi.fn(),
    getRun: vi.fn(),
    answer: vi.fn(),
    retry: vi.fn(),
    fileUrl: vi.fn((id: string, kind: string) => `/api/runs/${id}/files/${kind}`),
    listApplications: vi.fn().mockResolvedValue([]),
    updateApplication: vi.fn(),
    getProfile: vi.fn(),
    saveProfile: vi.fn(),
    getQuestions: vi.fn().mockResolvedValue([]),
    getAnswers: vi.fn().mockResolvedValue({}),
    saveAnswers: vi.fn().mockResolvedValue(undefined),
    draftProfile: vi.fn(),
  };
  return { ...base, ...overrides };
}

export const router = { push: vi.fn(), replace: vi.fn(), refresh: vi.fn(), back: vi.fn() };

vi.mock("next/navigation", () => ({
  useRouter: () => router,
  useParams: () => ({}),
  usePathname: () => "/",
}));
