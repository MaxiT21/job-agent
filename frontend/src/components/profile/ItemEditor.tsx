"use client";

import type { ReactNode } from "react";

import type { ProfileItem } from "@/lib/types";

export type Flags = Record<string, string[]>; // path -> reasons

const KIND_LABEL: Record<ProfileItem["kind"], string> = {
  experience: "Experience",
  project: "Project",
  education: "Education",
  skill: "Skills",
  certificate: "Certificate",
  language: "Language",
};

const input =
  "w-full rounded border border-line bg-paper px-2 py-1.5 text-sm focus:border-ink focus:outline-none";

/** Wraps a field and shows why it was flagged (something the answers don't support). */
export function Flagged({ reasons, children }: { reasons?: string[]; children: ReactNode }) {
  if (!reasons?.length) return <>{children}</>;
  return (
    <div data-flagged className="rounded border-l-4 border-terracotta bg-terracotta/5 py-1 pl-2">
      {children}
      {reasons.map((r) => (
        <p key={r} className="mt-1 text-xs text-terracotta">
          {r}
        </p>
      ))}
    </div>
  );
}

export function ItemEditor({
  item,
  index,
  flags,
  onChange,
  onRemove,
}: {
  item: ProfileItem;
  index: number;
  flags: Flags;
  onChange: (item: ProfileItem) => void;
  onRemove: () => void;
}) {
  const at = (field: string) => flags[`items[${index}].${field}`];
  const set = (patch: Partial<ProfileItem>) => onChange({ ...item, ...patch });
  const bullets = item.bullets ?? [];

  return (
    <fieldset className="space-y-2 rounded-lg border border-line bg-card p-4">
      <legend className="px-1 font-mono text-xs uppercase tracking-wider text-muted">
        {KIND_LABEL[item.kind]} · {item.id}
      </legend>
      <div className="grid gap-2 sm:grid-cols-3">
        <Flagged reasons={at("title")}>
          <input aria-label="Title" className={input} value={item.title} onChange={(e) => set({ title: e.target.value })} />
        </Flagged>
        <Flagged reasons={at("org")}>
          <input
            aria-label="Organisation"
            placeholder="Organisation"
            className={input}
            value={item.org ?? ""}
            onChange={(e) => set({ org: e.target.value || null })}
          />
        </Flagged>
        <Flagged reasons={at("period")}>
          <input
            aria-label="Period"
            placeholder="Period"
            className={input}
            value={item.period ?? ""}
            onChange={(e) => set({ period: e.target.value || null })}
          />
        </Flagged>
      </div>
      {bullets.map((b, j) => (
        <Flagged key={b.id} reasons={at(`bullets[${j}]`)}>
          <div className="flex items-start gap-2">
            <textarea
              aria-label={`Bullet ${j + 1}`}
              rows={2}
              className={input}
              value={b.text}
              onChange={(e) =>
                set({ bullets: bullets.map((x, k) => (k === j ? { ...x, text: e.target.value } : x)) })
              }
            />
            <button
              type="button"
              aria-label={`Remove bullet ${j + 1}`}
              onClick={() => set({ bullets: bullets.filter((_, k) => k !== j) })}
              className="px-1 text-muted hover:text-terracotta"
            >
              ×
            </button>
          </div>
        </Flagged>
      ))}
      <input
        aria-label="Tags"
        className={`${input} font-mono text-xs`}
        value={(item.tags ?? []).join(", ")}
        onChange={(e) =>
          set({ tags: e.target.value.split(",").map((t) => t.trim()).filter(Boolean) })
        }
      />
      <button type="button" onClick={onRemove} className="text-xs text-muted hover:text-terracotta">
        Remove this {KIND_LABEL[item.kind].toLowerCase()}
      </button>
    </fieldset>
  );
}
