import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AgentProvider } from "@/lib/agent-context";
import { ApiError } from "@/lib/http-client";
import { fakeAgent, router } from "@/test/fake-agent";

import { NewRunForm } from "./NewRunForm";

const POSTING = "Backend intern at Acme. Python, SQL and FastAPI. Barcelona, hybrid. Git required.";

beforeEach(() => vi.clearAllMocks());

function setup(agent = fakeAgent({ startRun: vi.fn().mockResolvedValue({ run_id: "r1" }) })) {
  render(
    <AgentProvider client={agent}>
      <NewRunForm />
    </AgentProvider>,
  );
  return agent;
}

describe("NewRunForm", () => {
  it("starts a run from pasted text and opens it", async () => {
    const agent = setup();
    await userEvent.type(screen.getByLabelText(/job posting/i), POSTING);
    await userEvent.click(screen.getByRole("button", { name: /tailor my application/i }));

    expect(agent.startRun).toHaveBeenCalledWith({ posting_text: POSTING });
    expect(router.push).toHaveBeenCalledWith("/runs/r1");
  });

  it("starts a run from a URL", async () => {
    const agent = setup();
    await userEvent.click(screen.getByRole("tab", { name: /url/i }));
    await userEvent.type(screen.getByLabelText(/posting url/i), "https://jobs.example.com/1");
    await userEvent.click(screen.getByRole("button", { name: /tailor my application/i }));

    expect(agent.startRun).toHaveBeenCalledWith({ posting_url: "https://jobs.example.com/1" });
  });

  it("needs enough text before starting", async () => {
    setup();
    await userEvent.type(screen.getByLabelText(/job posting/i), "too short");
    expect(screen.getByRole("button", { name: /tailor my application/i })).toBeDisabled();
  });

  it("shows the server's error", async () => {
    setup(fakeAgent({ startRun: vi.fn().mockRejectedValue(new ApiError(422, "posting_url: invalid")) }));
    await userEvent.click(screen.getByRole("tab", { name: /url/i }));
    await userEvent.type(screen.getByLabelText(/posting url/i), "https://x.example");
    await userEvent.click(screen.getByRole("button", { name: /tailor my application/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("posting_url: invalid");
    expect(router.push).not.toHaveBeenCalled();
  });
});
