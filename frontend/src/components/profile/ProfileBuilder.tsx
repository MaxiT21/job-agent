"use client";

import { useEffect, useRef, useState } from "react";

import { useAgent } from "@/lib/agent-context";
import type { GuidedSection, Profile, ProfileDraft } from "@/lib/types";

import { Button, Card, ErrorText, Spinner, errorMessage } from "../ui";
import { GuidedSections } from "./GuidedSections";
import { type Flags } from "./ItemEditor";
import { ProfileReview, toFlags } from "./ProfileReview";

const FOLLOW_UPS = "follow_ups";

export function ProfileBuilder({ saveDelayMs = 800 }: { saveDelayMs?: number }) {
  const agent = useAgent();
  const [sections, setSections] = useState<GuidedSection[]>([]);
  const [answers, setAnswers] = useState<Record<string, string> | null>(null);
  const [source, setSource] = useState<"custom" | "sample" | null>(null);
  const [draft, setDraft] = useState<ProfileDraft | null>(null);
  const [edited, setEdited] = useState<Profile | null>(null);
  const [flags, setFlags] = useState<Flags>({});
  const [busy, setBusy] = useState<"draft" | "save" | null>(null);
  const [saved, setSaved] = useState<"saving" | "saved" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    Promise.all([agent.getQuestions(), agent.getAnswers(), agent.getProfile()]).then(
      ([q, a, p]) => {
        setSections(q);
        setAnswers(a);
        setSource(p.source);
      },
      (e) => setError(errorMessage(e)),
    );
  }, [agent]);

  useEffect(() => () => clearTimeout(timer.current), []);

  function change(id: string, text: string) {
    if (!answers) return;
    const next = { ...answers, [id]: text };
    setAnswers(next);
    setSaved("saving");
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      agent.saveAnswers(next).then(
        () => setSaved("saved"),
        (e) => setError(errorMessage(e)),
      );
    }, saveDelayMs);
  }

  async function build() {
    if (!answers) return;
    setBusy("draft");
    setError(null);
    try {
      const d = await agent.draftProfile(answers);
      setDraft(d);
      setEdited(d.profile);
      setFlags(toFlags(d.flags));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(null);
    }
  }

  async function save() {
    if (!edited) return;
    setBusy("save");
    setError(null);
    try {
      const view = await agent.saveProfile(edited);
      setSource(view.source);
      setDraft(null);
      setEdited(null);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(null);
    }
  }

  if (!answers) return error ? <ErrorText>{error}</ErrorText> : <Spinner label="Loading…" />;
  const hasAnswers = Object.values(answers).some((v) => v.trim());

  return (
    <div className="space-y-10">
      <p className="text-sm">
        {source === "custom"
          ? "The agent is using your profile. Rebuild and save to update it."
          : "The agent is using the sample profile (a fictional candidate) until you save yours."}
      </p>

      <GuidedSections sections={sections} answers={answers} onChange={change} />

      <div className="flex flex-wrap items-center gap-4">
        <Button onClick={build} disabled={!hasAnswers || busy !== null || agent.demo}>
          {busy === "draft" ? "Building…" : draft ? "Rebuild my profile" : "Build my profile"}
        </Button>
        {busy === "draft" && <Spinner label="The AI is organising your answers (10–30 s)…" />}
        {saved && busy !== "draft" && (
          <span className="text-xs text-muted">{saved === "saving" ? "Saving…" : "Answers saved"}</span>
        )}
      </div>
      {error && <ErrorText>{error}</ErrorText>}

      {draft && edited && (
        <section className="space-y-6">
          <header className="space-y-1">
            <h2 className="font-serif text-3xl">Review your profile</h2>
            <p className="text-sm text-muted">
              The AI only organised what you wrote. Anything it could not find in your answers is
              highlighted: fix it or remove it. Every CV line the agent writes will cite these items.
            </p>
          </header>

          {draft.follow_up_questions.length > 0 && (
            <Card className="space-y-3">
              <h3 className="font-medium">Questions that would make your CV stronger</h3>
              <ul className="list-inside list-disc space-y-1 text-sm">
                {draft.follow_up_questions.map((q) => (
                  <li key={q}>{q}</li>
                ))}
              </ul>
              <label className="block space-y-1">
                <span className="text-sm text-muted">Answer here, then rebuild.</span>
                <textarea
                  aria-label="Answers to the follow-up questions"
                  rows={4}
                  value={answers[FOLLOW_UPS] ?? ""}
                  onChange={(e) => change(FOLLOW_UPS, e.target.value)}
                  className="w-full rounded-md border border-line bg-paper p-3 text-sm focus:border-ink focus:outline-none"
                />
              </label>
            </Card>
          )}

          <ProfileReview profile={edited} flags={flags} onChange={setEdited} />

          <Button onClick={save} disabled={busy !== null}>
            {busy === "save" ? "Saving…" : "Save profile"}
          </Button>
        </section>
      )}
    </div>
  );
}
