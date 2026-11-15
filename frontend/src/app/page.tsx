"use client";

import { AuthGate } from "@/components/AuthGate";
import { DemoScenarios } from "@/components/DemoScenarios";
import { NewRunForm } from "@/components/NewRunForm";
import { RunList } from "@/components/RunList";
import { useAgent } from "@/lib/agent-context";

export default function Home() {
  const agent = useAgent();
  return (
    <AuthGate>
      <div className="space-y-12">
        <header className="space-y-2">
          <h1 className="font-serif text-4xl">New application</h1>
          <p className="max-w-2xl text-muted">
            Paste a job posting. The agent extracts what the role needs, matches it against your
            profile, and drafts a CV and cover letter where every line cites your real experience.
            Nothing is created until you approve it.
          </p>
        </header>
        {agent.demo ? <DemoScenarios /> : <NewRunForm />}
        <section className="space-y-3">
          <h2 className="font-serif text-2xl">Recent runs</h2>
          <RunList />
        </section>
      </div>
    </AuthGate>
  );
}
