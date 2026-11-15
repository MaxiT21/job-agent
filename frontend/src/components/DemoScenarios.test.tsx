import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AgentProvider } from "@/lib/agent-context";
import { DemoClient } from "@/lib/demo-client";

import { DemoScenarios } from "./DemoScenarios";

describe("DemoScenarios", () => {
  it("links every recorded scenario", async () => {
    const demo = new DemoClient("/demo", 0);
    vi.spyOn(demo, "scenarios").mockResolvedValue([
      { id: "strong-match", title: "Strong match", description: "Fits well" },
      { id: "vague", title: "Vague posting", description: "The agent asks" },
    ]);
    render(
      <AgentProvider client={demo}>
        <DemoScenarios />
      </AgentProvider>,
    );

    expect(await screen.findByRole("link", { name: /strong match/i })).toHaveAttribute(
      "href",
      "/runs/strong-match",
    );
    expect(screen.getByRole("link", { name: /vague posting/i })).toHaveAttribute("href", "/runs/vague");
    expect(screen.getByText("The agent asks")).toBeInTheDocument();
  });
});
