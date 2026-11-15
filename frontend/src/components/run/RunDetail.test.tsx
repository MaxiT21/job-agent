import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AgentProvider } from "@/lib/agent-context";
import { fakeAgent } from "@/test/fake-agent";
import { profile, run } from "@/test/fixtures";

import { RunDetail } from "./RunDetail";

beforeEach(() => vi.clearAllMocks());

function setup(view = run(), overrides = {}) {
  const agent = fakeAgent({
    getRun: vi.fn().mockResolvedValue(view),
    getProfile: vi.fn().mockResolvedValue({ source: "sample", profile }),
    answer: vi.fn().mockResolvedValue(run({ status: "running", waiting_for: null })),
    retry: vi.fn().mockResolvedValue(run({ status: "running", waiting_for: null })),
    ...overrides,
  });
  render(
    <AgentProvider client={agent}>
      <RunDetail runId="r1" />
    </AgentProvider>,
  );
  return agent;
}

describe("RunDetail", () => {
  it("answers a clarifying question", async () => {
    const agent = setup(run({ waiting_for: { type: "clarify", question: "Which stack?" } }));
    await userEvent.type(await screen.findByLabelText(/which stack/i), "Python and Postgres");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));
    expect(agent.answer).toHaveBeenCalledWith("r1", { answer: "Python and Postgres" });
  });

  it("asks for the posting text when the URL was unreadable", async () => {
    const agent = setup(run({ waiting_for: { type: "paste_text", reason: "JS-only page" } }));
    expect(await screen.findByText(/JS-only page/)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText(/posting text/i), "We need a Python intern");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));
    expect(agent.answer).toHaveBeenCalledWith("r1", { text: "We need a Python intern" });
  });

  it("lets you apply anyway or stop on a low fit", async () => {
    const lowFit = run({
      waiting_for: { type: "low_fit", score: 30, gaps: ["r3"], summary: "Weak match" },
    });
    const agent = setup(lowFit);
    expect(await screen.findByText(/30/)).toBeInTheDocument();
    expect(screen.getAllByText("Kubernetes").length).toBeGreaterThan(0); // gap shown by name
    await userEvent.click(screen.getByRole("button", { name: /apply anyway/i }));
    expect(agent.answer).toHaveBeenCalledWith("r1", { proceed: true });
  });

  it("approves the documents", async () => {
    const agent = setup();
    await userEvent.click(await screen.findByRole("button", { name: /approve/i }));
    expect(agent.answer).toHaveBeenCalledWith("r1", { approved: true });
  });

  it("requests changes with notes", async () => {
    const agent = setup();
    await userEvent.click(await screen.findByRole("button", { name: /request changes/i }));
    await userEvent.type(screen.getByLabelText(/what should change/i), "Shorter summary");
    await userEvent.click(screen.getByRole("button", { name: /regenerate/i }));
    expect(agent.answer).toHaveBeenCalledWith("r1", { approved: false, notes: "Shorter summary" });
  });

  it("shows the profile text behind an evidence chip", async () => {
    setup();
    const table = await screen.findByRole("table", { name: /requirements/i });
    const chip = within(table).getAllByRole("button", { name: "proj-network-monitor-b1" })[0];
    await userEvent.hover(chip);
    expect(await screen.findByRole("tooltip")).toHaveTextContent(
      "Built a FastAPI backend that scans the local network.",
    );
  });

  it("shows what the verifier caught and that it was fixed", async () => {
    setup();
    const panel = await screen.findByRole("region", { name: /fact-check/i });
    expect(panel).toHaveTextContent("Number not in evidence: 5");
    expect(panel).toHaveTextContent(/caught 1 issue/i);
    expect(panel).toHaveTextContent(/passed/i);
  });

  it("offers retry on error", async () => {
    const agent = setup(run({ status: "error", error: "Gemini 503", waiting_for: null }));
    expect(await screen.findByText(/Gemini 503/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(agent.retry).toHaveBeenCalledWith("r1");
  });

  it("links the documents when done", async () => {
    setup(run({ status: "done", waiting_for: null, files: { cv: true, cover_letter: true } }));
    expect(await screen.findByRole("link", { name: /download cv/i })).toHaveAttribute(
      "href",
      "/api/runs/r1/files/cv",
    );
    expect(screen.getByRole("link", { name: /download cover letter/i })).toHaveAttribute(
      "href",
      "/api/runs/r1/files/cover_letter",
    );
  });

  it("shows progress while running and polls until it pauses", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const getRun = vi
      .fn()
      .mockResolvedValueOnce(run({ status: "running", step: "tailor_cv", waiting_for: null }))
      .mockResolvedValue(run());
    setup(undefined, { getRun });

    expect(await screen.findByText(/tailoring your cv/i)).toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(1600));
    expect(await screen.findByRole("button", { name: /approve/i })).toBeInTheDocument();
    expect(getRun).toHaveBeenCalledTimes(2);
    vi.useRealTimers();
  });
});
