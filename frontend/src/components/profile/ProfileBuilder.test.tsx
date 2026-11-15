import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AgentProvider } from "@/lib/agent-context";
import type { GuidedSection, ProfileDraft } from "@/lib/types";
import { fakeAgent } from "@/test/fake-agent";
import { profile } from "@/test/fixtures";

import { ProfileBuilder } from "./ProfileBuilder";

const questions: GuidedSection[] = [
  { id: "basics", title: "About you", prompt: "Name and contact.", hints: ["Full name"], optional: false },
  {
    id: "experience",
    title: "Work experience",
    prompt: "Jobs and internships.",
    hints: ["Company, role, dates"],
    optional: false,
  },
];

const draft: ProfileDraft = {
  profile: {
    ...profile,
    items: [
      {
        id: "exp-data-intern",
        kind: "experience",
        title: "Data Intern",
        org: "Acme Analytics",
        period: "2026",
        bullets: [{ id: "exp-data-intern-b1", text: "Built dashboards used by 40 managers.", tags: [] }],
        tags: ["power bi"],
      },
    ],
  },
  follow_up_questions: ["Which SQL database did you use?"],
  flags: [
    {
      path: "items[0].bullets[0]",
      text: "Built dashboards used by 40 managers.",
      reason: "Number not in your answers: 40",
    },
  ],
};

beforeEach(() => vi.clearAllMocks());

function setup(overrides = {}) {
  const agent = fakeAgent({
    getQuestions: vi.fn().mockResolvedValue(questions),
    getAnswers: vi.fn().mockResolvedValue({ basics: "Maria Lopez" }),
    getProfile: vi.fn().mockResolvedValue({ source: "sample", profile }),
    draftProfile: vi.fn().mockResolvedValue(draft),
    saveProfile: vi.fn().mockResolvedValue({ source: "custom", profile: draft.profile }),
    ...overrides,
  });
  render(
    <AgentProvider client={agent}>
      <ProfileBuilder saveDelayMs={10} />
    </AgentProvider>,
  );
  return agent;
}

describe("ProfileBuilder", () => {
  it("says which profile the agent is using", async () => {
    setup();
    expect(await screen.findByText(/using the sample profile/i)).toBeInTheDocument();
  });

  it("autosaves answers", async () => {
    const agent = setup();
    const box = await screen.findByLabelText(/work experience/i);
    await userEvent.type(box, "Data intern at Acme");
    await vi.waitFor(() =>
      expect(agent.saveAnswers).toHaveBeenLastCalledWith({
        basics: "Maria Lopez",
        experience: "Data intern at Acme",
      }),
    );
  });

  it("builds a draft, highlights unsupported facts and lists follow-up questions", async () => {
    const agent = setup();
    await userEvent.click(await screen.findByRole("button", { name: /build my profile/i }));

    expect(agent.draftProfile).toHaveBeenCalledWith({ basics: "Maria Lopez" });
    const flagged = await screen.findByText("Number not in your answers: 40");
    expect(flagged.closest("[data-flagged]")).not.toBeNull();
    expect(screen.getByText("Which SQL database did you use?")).toBeInTheDocument();
  });

  it("saves the edited draft", async () => {
    const agent = setup();
    await userEvent.click(await screen.findByRole("button", { name: /build my profile/i }));

    const bullet = await screen.findByDisplayValue("Built dashboards used by 40 managers.");
    await userEvent.clear(bullet);
    await userEvent.type(bullet, "Built dashboards used by 12 managers.");
    await userEvent.click(screen.getByRole("button", { name: /save profile/i }));

    const saved = vi.mocked(agent.saveProfile).mock.calls[0][0];
    expect(saved.items[0].bullets?.[0].text).toBe("Built dashboards used by 12 managers.");
    expect(await screen.findByText(/using your profile/i)).toBeInTheDocument();
  });

  it("can remove a bullet before saving", async () => {
    const agent = setup();
    await userEvent.click(await screen.findByRole("button", { name: /build my profile/i }));
    const item = (await screen.findByDisplayValue("Data Intern")).closest("fieldset")!;
    await userEvent.click(within(item as HTMLElement).getByRole("button", { name: /remove bullet 1/i }));
    await userEvent.click(screen.getByRole("button", { name: /save profile/i }));

    expect(vi.mocked(agent.saveProfile).mock.calls[0][0].items[0].bullets).toEqual([]);
  });
});
