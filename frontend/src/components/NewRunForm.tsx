"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { useAgent } from "@/lib/agent-context";

import { Button, ErrorText, errorMessage } from "./ui";

const MIN_TEXT = 50;

export function NewRunForm() {
  const agent = useAgent();
  const router = useRouter();
  const [mode, setMode] = useState<"text" | "url">("text");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ready =
    mode === "text" ? text.trim().length >= MIN_TEXT : /^https?:\/\/\S+$/.test(url.trim());

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const run = await agent.startRun(
        mode === "text" ? { posting_text: text.trim() } : { posting_url: url.trim() },
      );
      router.push(`/runs/${run.run_id}`);
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  const tab = (value: "text" | "url", label: string) => (
    <button
      type="button"
      role="tab"
      aria-selected={mode === value}
      onClick={() => setMode(value)}
      className={`border-b-2 px-1 pb-1 text-sm ${
        mode === value ? "border-terracotta text-ink" : "border-transparent text-muted"
      }`}
    >
      {label}
    </button>
  );

  return (
    <form onSubmit={submit} className="space-y-4">
      <div role="tablist" className="flex gap-4">
        {tab("text", "Paste the posting")}
        {tab("url", "From a URL")}
      </div>
      {mode === "text" ? (
        <label className="block">
          <span className="sr-only">Job posting</span>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={10}
            placeholder="Paste the whole job posting here…"
            className="w-full rounded-md border border-line bg-card p-3 text-sm focus:border-ink focus:outline-none"
          />
        </label>
      ) : (
        <label className="block">
          <span className="sr-only">Posting URL</span>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://…"
            className="w-full rounded-md border border-line bg-card p-3 text-sm focus:border-ink focus:outline-none"
          />
        </label>
      )}
      {error && <ErrorText>{error}</ErrorText>}
      <div className="flex flex-wrap items-center gap-4">
        <Button type="submit" disabled={!ready || busy}>
          {busy ? "Starting…" : "Tailor my application"}
        </Button>
        <span className="text-xs text-muted">
          Takes 1–2 minutes. You review everything before any file is created.
        </span>
      </div>
    </form>
  );
}
