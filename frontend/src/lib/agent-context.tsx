"use client";

import { createContext, type ReactNode, useContext, useEffect, useState } from "react";

import { getAgent } from "./agent";
import type { AgentClient } from "./client";

const AgentContext = createContext<AgentClient | null>(null);

/** Provides the build's AgentClient (or `client` in tests). Children render once it is ready. */
export function AgentProvider({ client, children }: { client?: AgentClient; children: ReactNode }) {
  const [agent, setAgent] = useState<AgentClient | null>(client ?? null);
  useEffect(() => {
    if (!client) getAgent().then(setAgent);
  }, [client]);
  if (!agent) return null;
  return <AgentContext.Provider value={agent}>{children}</AgentContext.Provider>;
}

export function useAgent(): AgentClient {
  const agent = useContext(AgentContext);
  if (!agent) throw new Error("useAgent must be used inside <AgentProvider>");
  return agent;
}
