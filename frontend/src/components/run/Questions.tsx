"use client";

import { type FormEvent, useState } from "react";

import type { JobPosting } from "@/lib/types";

import { Button } from "../ui";

type Answer = (value: Record<string, unknown>) => void;

/** A free-text question (clarify) or a request to paste the posting (paste_text). */
export function TextQuestion({
  label,
  hint,
  field,
  multiline,
  busy,
  onAnswer,
}: {
  label: string;
  hint?: string;
  field: "answer" | "text";
  multiline?: boolean;
  busy: boolean;
  onAnswer: Answer;
}) {
  const [value, setValue] = useState("");
  function submit(e: FormEvent) {
    e.preventDefault();
    onAnswer({ [field]: value.trim() });
  }
  const cls =
    "w-full rounded-md border border-line bg-paper p-3 text-sm focus:border-ink focus:outline-none";
  return (
    <form onSubmit={submit} className="space-y-3">
      <label className="block space-y-1">
        <span className="block font-medium">{label}</span>
        {hint && <span className="block text-sm text-muted">{hint}</span>}
        {multiline ? (
          <textarea rows={8} value={value} onChange={(e) => setValue(e.target.value)} className={cls} />
        ) : (
          <input value={value} onChange={(e) => setValue(e.target.value)} className={cls} />
        )}
      </label>
      <Button type="submit" disabled={!value.trim() || busy}>
        Send
      </Button>
    </form>
  );
}

export function LowFitQuestion({
  score,
  gaps,
  summary,
  posting,
  busy,
  onAnswer,
}: {
  score: number;
  gaps: string[];
  summary: string;
  posting?: JobPosting | null;
  busy: boolean;
  onAnswer: Answer;
}) {
  const names = Object.fromEntries((posting?.requirements ?? []).map((r) => [r.id, r.text]));
  return (
    <div className="space-y-3">
      <p className="font-medium">
        Low fit: <span className="font-mono">{Math.round(score)}</span>/100. Apply anyway?
      </p>
      <p className="text-sm text-muted">{summary}</p>
      {gaps.length > 0 && (
        <p className="text-sm">
          Missing:{" "}
          {gaps.map((g, i) => (
            <span key={g}>
              {i > 0 && ", "}
              <span>{names[g] ?? g}</span>
            </span>
          ))}
        </p>
      )}
      <div className="flex gap-3">
        <Button onClick={() => onAnswer({ proceed: true })} disabled={busy}>
          Apply anyway
        </Button>
        <Button variant="secondary" onClick={() => onAnswer({ proceed: false })} disabled={busy}>
          Stop here
        </Button>
      </div>
    </div>
  );
}

export function ApprovalControls({ busy, onAnswer }: { busy: boolean; onAnswer: Answer }) {
  const [editing, setEditing] = useState(false);
  const [notes, setNotes] = useState("");
  if (editing) {
    return (
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onAnswer({ approved: false, notes: notes.trim() });
        }}
        className="space-y-3"
      >
        <label className="block space-y-1">
          <span className="block font-medium">What should change?</span>
          <span className="block text-sm text-muted">
            Both documents are regenerated with your notes and checked again. The agent still
            can&apos;t add anything that isn&apos;t in your profile.
          </span>
          <textarea
            rows={4}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full rounded-md border border-line bg-paper p-3 text-sm focus:border-ink focus:outline-none"
          />
        </label>
        <div className="flex gap-3">
          <Button type="submit" disabled={!notes.trim() || busy}>
            Regenerate
          </Button>
          <Button type="button" variant="ghost" onClick={() => setEditing(false)}>
            Cancel
          </Button>
        </div>
      </form>
    );
  }
  return (
    <div className="flex flex-wrap gap-3">
      <Button onClick={() => onAnswer({ approved: true })} disabled={busy}>
        Approve and create the documents
      </Button>
      <Button variant="secondary" onClick={() => setEditing(true)} disabled={busy}>
        Request changes
      </Button>
    </div>
  );
}
