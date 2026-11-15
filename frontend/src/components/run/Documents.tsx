import type { Evidence } from "@/lib/evidence";
import type { CoverLetter, TailoredCV } from "@/lib/types";

import { EvidenceList } from "./EvidenceChip";

/** The CV as it will be rendered, with the evidence behind every line. */
export function CvPreview({ cv, evidence }: { cv: TailoredCV; evidence: Evidence }) {
  return (
    <div className="space-y-4 text-sm">
      <div>
        <p>{cv.summary.text}</p>
        <EvidenceList ids={cv.summary.evidence_ids} text={evidence.text} />
      </div>
      {cv.entries.map((entry) => {
        const item = evidence.items[entry.item_id];
        return (
          <div key={entry.item_id}>
            <p className="font-medium">
              {item?.title ?? entry.item_id}
              {item?.org && <span className="font-normal text-muted"> — {item.org}</span>}
              {item?.period && <span className="font-normal italic text-muted"> ({item.period})</span>}
            </p>
            <ul className="mt-1 space-y-1.5">
              {entry.bullets.map((b, i) => (
                <li key={i} className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                  <span>• {b.text}</span>
                  <EvidenceList ids={b.evidence_ids} text={evidence.text} />
                </li>
              ))}
            </ul>
          </div>
        );
      })}
      {cv.skills.length > 0 && (
        <p>
          <span className="font-medium">Skills: </span>
          {cv.skills.join(", ")}
        </p>
      )}
    </div>
  );
}

export function LetterPreview({ letter, evidence }: { letter: CoverLetter; evidence: Evidence }) {
  return (
    <div className="space-y-3 text-sm leading-relaxed">
      {letter.paragraphs.map((p, i) => (
        <div key={i}>
          <p>{p.text}</p>
          <EvidenceList ids={p.evidence_ids} text={evidence.text} />
        </div>
      ))}
    </div>
  );
}
