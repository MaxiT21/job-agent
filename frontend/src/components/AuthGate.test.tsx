import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AgentProvider } from "@/lib/agent-context";
import { fakeAgent, router } from "@/test/fake-agent";

import { AuthGate } from "./AuthGate";

beforeEach(() => vi.clearAllMocks());

describe("AuthGate", () => {
  it("sends logged-out users to /login", async () => {
    render(
      <AgentProvider client={fakeAgent({ me: vi.fn().mockResolvedValue(false) })}>
        <AuthGate>secret</AuthGate>
      </AgentProvider>,
    );
    await vi.waitFor(() => expect(router.replace).toHaveBeenCalledWith("/login"));
    expect(screen.queryByText("secret")).not.toBeInTheDocument();
  });

  it("shows the page to logged-in users", async () => {
    render(
      <AgentProvider client={fakeAgent()}>
        <AuthGate>secret</AuthGate>
      </AgentProvider>,
    );
    expect(await screen.findByText("secret")).toBeInTheDocument();
  });
});
