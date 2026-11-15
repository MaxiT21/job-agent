"use client";

import { useId, useState } from "react";

/** A profile ID; hover or focus shows what the profile actually says. */
export function EvidenceChip({ id, text }: { id: string; text?: string }) {
  const [open, setOpen] = useState(false);
  const tipId = useId();
  return (
    <span className="relative inline-block">
      <button
        type="button"
        aria-describedby={open ? tipId : undefined}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        className="rounded border border-line bg-paper px-1.5 py-0.5 font-mono text-[11px] text-muted hover:border-ink hover:text-ink"
      >
        {id}
      </button>
      {open && (
        <span
          id={tipId}
          role="tooltip"
          className="absolute bottom-full left-0 z-10 mb-1 w-72 rounded-md bg-ink p-2.5 text-xs leading-relaxed text-paper shadow-lg"
        >
          {text ?? "Not in the current profile"}
        </span>
      )}
    </span>
  );
}

export function EvidenceList({ ids, text }: { ids: string[]; text: Record<string, string> }) {
  if (ids.length === 0) return <span className="text-xs text-muted">—</span>;
  return (
    <span className="flex flex-wrap gap-1">
      {ids.map((id) => (
        <EvidenceChip key={id} id={id} text={text[id]} />
      ))}
    </span>
  );
}
