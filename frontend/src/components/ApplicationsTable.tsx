"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAgent } from "@/lib/agent-context";
import { formatDate } from "@/lib/format";
import type { Application, ApplicationStatus } from "@/lib/types";

import { ErrorText, errorMessage } from "./ui";

const STATUSES: { value: ApplicationStatus; label: string }[] = [
  { value: "ready", label: "Ready to send" },
  { value: "applied", label: "Applied" },
  { value: "interview", label: "Interview" },
  { value: "offer", label: "Offer" },
  { value: "rejected", label: "Rejected" },
  { value: "withdrawn", label: "Withdrawn" },
];

export function ApplicationsTable() {
  const agent = useAgent();
  const [apps, setApps] = useState<Application[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    agent.listApplications().then(setApps, (e) => setError(errorMessage(e)));
  }, [agent]);

  async function change(runId: string, status: ApplicationStatus) {
    setError(null);
    try {
      const updated = await agent.updateApplication(runId, status);
      setApps((list) => list?.map((a) => (a.run_id === runId ? updated : a)) ?? null);
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  if (!apps) return error ? <ErrorText>{error}</ErrorText> : null;
  if (apps.length === 0)
    return <p className="text-sm text-muted">Approved applications appear here.</p>;

  return (
    <div className="space-y-3">
      {error && <ErrorText>{error}</ErrorText>}
      <div className="overflow-x-auto rounded-lg border border-line bg-card">
        <table className="w-full text-left text-sm">
          <thead className="text-xs uppercase tracking-wider text-muted">
            <tr>
              <th className="px-4 py-2 font-normal">Role</th>
              <th className="px-4 py-2 font-normal">Fit</th>
              <th className="px-4 py-2 font-normal">Created</th>
              <th className="px-4 py-2 font-normal">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {apps.map((a) => (
              <tr key={a.run_id}>
                <td className="px-4 py-3">
                  <Link href={`/runs/${a.run_id}`} className="font-medium hover:text-terracotta">
                    {a.title}
                  </Link>
                  <span className="block text-xs text-muted">
                    {[a.company, a.location].filter(Boolean).join(" · ")}
                  </span>
                </td>
                <td className="px-4 py-3 font-mono">{Math.round(a.fit_score)}</td>
                <td className="px-4 py-3 text-muted">{formatDate(a.created_at)}</td>
                <td className="px-4 py-3">
                  <select
                    aria-label={`Status of ${a.title} at ${a.company}`}
                    value={a.status}
                    onChange={(e) => change(a.run_id, e.target.value as ApplicationStatus)}
                    className="rounded-md border border-line bg-paper px-2 py-1 text-sm"
                  >
                    {STATUSES.map((s) => (
                      <option key={s.value} value={s.value}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
