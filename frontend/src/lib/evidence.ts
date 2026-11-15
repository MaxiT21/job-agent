"use client";

import { useEffect, useState } from "react";

import { useAgent } from "./agent-context";
import type { Profile, ProfileItem } from "./types";

export type Evidence = {
  /** What each profile ID says: an item's header, or a bullet's text. */
  text: Record<string, string>;
  items: Record<string, ProfileItem>;
};

export const NO_EVIDENCE: Evidence = { text: {}, items: {} };

export function buildEvidence(profile: Profile): Evidence {
  const text: Record<string, string> = {};
  const items: Record<string, ProfileItem> = {};
  for (const item of profile.items) {
    items[item.id] = item;
    text[item.id] = [item.title, item.org, item.period].filter(Boolean).join(" · ");
    for (const b of item.bullets ?? []) text[b.id] = b.text;
  }
  return { text, items };
}

/** The profile the agent cites, as an ID → text lookup. */
export function useEvidence(): Evidence {
  const agent = useAgent();
  const [evidence, setEvidence] = useState<Evidence>(NO_EVIDENCE);
  useEffect(() => {
    agent.getProfile().then(
      (p) => setEvidence(buildEvidence(p.profile)),
      () => setEvidence(NO_EVIDENCE),
    );
  }, [agent]);
  return evidence;
}
