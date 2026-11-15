"use client";

import type { GuidedSection } from "@/lib/types";

/** One free-text box per guided section, with what to include. */
export function GuidedSections({
  sections,
  answers,
  onChange,
}: {
  sections: GuidedSection[];
  answers: Record<string, string>;
  onChange: (id: string, text: string) => void;
}) {
  return (
    <ol className="space-y-6">
      {sections.map((s, i) => (
        <li key={s.id}>
          <label className="block space-y-1.5">
            <span className="flex items-baseline gap-2">
              <span className="font-mono text-xs text-muted">{String(i + 1).padStart(2, "0")}</span>
              <span className="font-serif text-xl">{s.title}</span>
              {s.optional && <span className="text-xs text-muted">optional</span>}
            </span>
            <span className="block text-sm text-muted">{s.prompt}</span>
            <ul className="list-inside list-disc text-xs text-muted">
              {s.hints.map((h) => (
                <li key={h}>{h}</li>
              ))}
            </ul>
            <textarea
              aria-label={s.title}
              rows={s.id === "cv_text" ? 8 : 5}
              value={answers[s.id] ?? ""}
              onChange={(e) => onChange(s.id, e.target.value)}
              className="w-full rounded-md border border-line bg-card p-3 text-sm focus:border-ink focus:outline-none"
            />
          </label>
        </li>
      ))}
    </ol>
  );
}
