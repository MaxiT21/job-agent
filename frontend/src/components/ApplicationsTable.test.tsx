import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AgentProvider } from "@/lib/agent-context";
import type { Application } from "@/lib/types";
import { fakeAgent } from "@/test/fake-agent";

import { ApplicationsTable } from "./ApplicationsTable";

const app: Application = {
  run_id: "r1",
  created_at: "2026-11-15T10:00:00Z",
  company: "Acme",
  title: "Backend Intern",
  location: "Barcelona",
  fit_score: 80,
  cv_path: "/x/cv.docx",
  letter_path: "/x/cover_letter.docx",
  status: "ready",
};

describe("ApplicationsTable", () => {
  it("updates an application's status", async () => {
    const agent = fakeAgent({
      listApplications: vi.fn().mockResolvedValue([app]),
      updateApplication: vi.fn().mockResolvedValue({ ...app, status: "applied" }),
    });
    render(
      <AgentProvider client={agent}>
        <ApplicationsTable />
      </AgentProvider>,
    );

    const select = await screen.findByLabelText(/status of backend intern at acme/i);
    await userEvent.selectOptions(select, "applied");

    expect(agent.updateApplication).toHaveBeenCalledWith("r1", "applied");
    expect(select).toHaveValue("applied");
    expect(screen.getByRole("link", { name: /backend intern/i })).toHaveAttribute("href", "/runs/r1");
  });

  it("has an empty state", async () => {
    render(
      <AgentProvider client={fakeAgent()}>
        <ApplicationsTable />
      </AgentProvider>,
    );
    expect(await screen.findByText(/approved applications appear here/i)).toBeInTheDocument();
  });
});
