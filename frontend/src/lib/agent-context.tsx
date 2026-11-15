"use client";

import { createContext, type ReactNode, useContext, useState } from "react";

import { createAgent } from "./agent";
import type { AgentClient } from "./client";

const AgentContext = createContext<AgentClient | null>(null);

/** Provides the build's AgentClient (or `client` in tests). Renders children immediately. */
export function AgentProvider({ client, children }: { client?: AgentClient; children: ReactNode }) {
  const [agent] = useState<AgentClient>(() => client ?? createAgent());
  return <AgentContext.Provider value={agent}>{children}</AgentContext.Provider>;
}

export function useAgent(): AgentClient {
  const agent = useContext(AgentContext);
  if (!agent) throw new Error("useAgent must be used inside <AgentProvider>");
  return agent;
}
