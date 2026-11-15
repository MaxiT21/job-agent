"use client";

import { useCallback, useEffect, useState } from "react";

import { errorMessage } from "@/components/ui";

import { useAgent } from "./agent-context";
import type { RunView } from "./types";

export const POLL_MS = 1500;

/** Loads a run and keeps polling while it is running. `act` runs a mutation that returns a RunView. */
export function useRun(runId: string) {
  const agent = useAgent();
  const [run, setRun] = useState<RunView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    agent.getRun(runId).then(
      (r) => {
        setRun(r);
        setError(null);
      },
      (e) => setError(errorMessage(e)),
    );
  }, [agent, runId]);

  useEffect(load, [load]);

  useEffect(() => {
    if (run?.status !== "running") return;
    const t = setTimeout(load, POLL_MS);
    return () => clearTimeout(t);
  }, [run, load]);

  const act = useCallback(async (mutation: () => Promise<RunView>) => {
    setBusy(true);
    setError(null);
    try {
      setRun(await mutation());
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }, []);

  return { run, error, busy, act };
}
