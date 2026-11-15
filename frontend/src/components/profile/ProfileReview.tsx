"use client";

import type { DraftFlag, Profile } from "@/lib/types";

import { type Flags, Flagged, ItemEditor } from "./ItemEditor";

const input =
  "w-full rounded border border-line bg-paper px-2 py-1.5 text-sm focus:border-ink focus:outline-none";

export function toFlags(flags: DraftFlag[]): Flags {
  const out: Flags = {};
  for (const f of flags) (out[f.path] ??= []).push(f.reason);
  return out;
}

/** The AI's draft, fully editable, with unsupported facts highlighted. */
export function ProfileReview({
  profile,
  flags,
  onChange,
}: {
  profile: Profile;
  flags: Flags;
  onChange: (p: Profile) => void;
}) {
  const set = (patch: Partial<Profile>) => onChange({ ...profile, ...patch });
  return (
    <div className="space-y-4">
      <div className="grid gap-2 sm:grid-cols-3">
        <input aria-label="Name" className={input} value={profile.name} onChange={(e) => set({ name: e.target.value })} />
        <input aria-label="Email" className={input} value={profile.email} onChange={(e) => set({ email: e.target.value })} />
        <input
          aria-label="Location"
          className={input}
          value={profile.location}
          onChange={(e) => set({ location: e.target.value })}
        />
      </div>
      <Flagged reasons={flags.summary}>
        <textarea
          aria-label="Summary"
          rows={2}
          className={input}
          value={profile.summary}
          onChange={(e) => set({ summary: e.target.value })}
        />
      </Flagged>
      {profile.items.map((item, i) => (
        <ItemEditor
          key={item.id}
          item={item}
          index={i}
          flags={flags}
          onChange={(next) => set({ items: profile.items.map((x, k) => (k === i ? next : x)) })}
          onRemove={() => set({ items: profile.items.filter((_, k) => k !== i) })}
        />
      ))}
    </div>
  );
}
