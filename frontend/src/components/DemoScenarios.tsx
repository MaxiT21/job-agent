"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAgent } from "@/lib/agent-context";
import { DemoClient, type DemoScenario } from "@/lib/demo-client";

/** Demo home: one card per recorded run. */
export function DemoScenarios() {
  const agent = useAgent();
  const [scenarios, setScenarios] = useState<DemoScenario[]>([]);

  useEffect(() => {
    if (agent instanceof DemoClient) agent.scenarios().then(setScenarios);
  }, [agent]);

  return (
    <section className="space-y-3">
      <p className="text-sm text-muted">
        Pick a recorded run. You answer the agent&apos;s questions and approve exactly as in the
        private app; every result was produced by the real agent (Gemini) for a fictional
        candidate.
      </p>
      <ul className="grid gap-4 sm:grid-cols-2">
        {scenarios.map((s) => (
          <li key={s.id}>
            <Link
              href={`/runs/${s.id}`}
              className="block h-full rounded-lg border border-line bg-card p-5 transition-colors hover:border-ink"
            >
              <span className="block font-serif text-xl">{s.title}</span>
              <span className="mt-1 block text-sm text-muted">{s.description}</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
