"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { Button, Card, ErrorText, errorMessage } from "@/components/ui";
import { useAgent } from "@/lib/agent-context";

export default function LoginPage() {
  const agent = useAgent();
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await agent.login(password);
      router.replace("/");
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto mt-16 max-w-sm">
      <Card>
        <h1 className="mb-1 font-serif text-2xl">Welcome back</h1>
        <p className="mb-5 text-sm text-muted">This is a private app. Enter your password.</p>
        <form onSubmit={submit} className="space-y-4">
          <label className="block">
            <span className="mb-1 block text-sm">Password</span>
            <input
              type="password"
              autoComplete="current-password"
              autoFocus
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-line bg-paper p-2.5 text-sm focus:border-ink focus:outline-none"
            />
          </label>
          {error && <ErrorText>{error}</ErrorText>}
          <Button type="submit" disabled={!password || busy} className="w-full">
            {busy ? "Checking…" : "Log in"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
