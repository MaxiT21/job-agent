"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAgent } from "@/lib/agent-context";
import { formatDate } from "@/lib/format";
import type { RunSummary } from "@/lib/types";

import { StatusChip } from "./StatusChip";
import { ErrorText, errorMessage } from "./ui";

export function RunList() {
  const agent = useAgent();
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    agent.listRuns().then(setRuns, (e) => setError(errorMessage(e)));
  }, [agent]);

  if (error) return <ErrorText>{error}</ErrorText>;
  if (!runs) return null;
  if (runs.length === 0) return <p className="text-sm text-muted">No applications yet.</p>;

  return (
    <ul className="divide-y divide-line rounded-lg border border-line bg-card">
      {runs.map((r) => (
        <li key={r.run_id} className="flex items-center gap-4 px-4 py-3">
          <Link href={`/runs/${r.run_id}`} className="min-w-0 flex-1 hover:text-terracotta">
            <span className="block truncate font-medium">{r.title ?? "Reading the posting…"}</span>
            <span className="block truncate text-xs text-muted">
              {[r.company, formatDate(r.created_at)].filter(Boolean).join(" · ")}
            </span>
          </Link>
          {r.fit_score != null && (
            <span className="font-mono text-sm" title="Fit score">
              {Math.round(r.fit_score)}
            </span>
          )}
          <StatusChip status={r.status} />
        </li>
      ))}
    </ul>
  );
}
