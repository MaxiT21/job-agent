import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AgentProvider, useAgent } from "./agent-context";

function WhichClient() {
  return <span>{useAgent().demo ? "demo" : "live"}</span>;
}

describe("AgentProvider", () => {
  it("renders children immediately with the build's client (no async gap)", () => {
    render(
      <AgentProvider>
        <WhichClient />
      </AgentProvider>,
    );
    expect(screen.getByText("live")).toBeInTheDocument();
  });
});
