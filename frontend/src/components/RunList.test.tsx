import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AgentProvider } from "@/lib/agent-context";
import { fakeAgent } from "@/test/fake-agent";

import { RunList } from "./RunList";

describe("RunList", () => {
  it("lists runs with status and links", async () => {
    const agent = fakeAgent({
      listRuns: vi.fn().mockResolvedValue([
        {
          run_id: "r1",
          created_at: "2026-11-15T10:00:00Z",
          status: "waiting",
          company: "Acme",
          title: "Backend Intern",
          fit_score: 80,
        },
        { run_id: "r2", created_at: null, status: "running", company: null, title: null, fit_score: null },
      ]),
    });
    render(
      <AgentProvider client={agent}>
        <RunList />
      </AgentProvider>,
    );

    const link = await screen.findByRole("link", { name: /backend intern/i });
    expect(link).toHaveAttribute("href", "/runs/r1");
    expect(screen.getByText(/needs you/i)).toBeInTheDocument();
    expect(screen.getByText("80")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /reading the posting/i })).toHaveAttribute("href", "/runs/r2");
  });

  it("has an empty state", async () => {
    render(
      <AgentProvider client={fakeAgent()}>
        <RunList />
      </AgentProvider>,
    );
    expect(await screen.findByText(/no applications yet/i)).toBeInTheDocument();
  });
});
