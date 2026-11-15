import type { Evidence } from "@/lib/evidence";
import type { FitReport, JobPosting } from "@/lib/types";

import { EvidenceList } from "./EvidenceChip";

const STATUS_STYLE = {
  met: "text-met",
  partial: "text-partial",
  gap: "text-gap",
} as const;

export function FitScore({ score }: { score: number }) {
  return (
    <div className="flex items-baseline gap-2">
      <span className="font-serif text-5xl">{Math.round(score)}</span>
      <span className="text-sm text-muted">/ 100 fit</span>
    </div>
  );
}

/** Requirement → met/partial/gap → the profile evidence behind it. */
export function EvidenceTable({
  fit,
  posting,
  evidence,
}: {
  fit: FitReport;
  posting?: JobPosting | null;
  evidence: Evidence;
}) {
  const reqs = Object.fromEntries((posting?.requirements ?? []).map((r) => [r.id, r]));
  return (
    <div>
      <table aria-label="Requirements" className="w-full text-left text-sm">
        <thead className="text-xs uppercase tracking-wider text-muted">
          <tr>
            <th className="py-2 pr-4 font-normal">Requirement</th>
            <th className="py-2 pr-4 font-normal">Match</th>
            <th className="py-2 font-normal">Evidence in your profile</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {fit.matches.map((m) => {
            const req = reqs[m.requirement_id];
            return (
              <tr key={m.requirement_id} className="align-top">
                <td className="py-2.5 pr-4">
                  <span className="block">{req?.text ?? m.requirement_id}</span>
                  <span className="text-xs text-muted">
                    {req?.importance === "must" ? "must have" : "nice to have"} · {m.note}
                  </span>
                </td>
                <td className={`py-2.5 pr-4 font-mono text-xs uppercase ${STATUS_STYLE[m.status]}`}>
                  {m.status}
                </td>
                <td className="py-2.5">
                  <EvidenceList ids={m.evidence_ids ?? []} text={evidence.text} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
