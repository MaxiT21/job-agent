"use client";

import { useAgent } from "@/lib/agent-context";
import { useEvidence } from "@/lib/evidence";
import { formatCost, STEP_LABEL } from "@/lib/format";
import type { RunView } from "@/lib/types";
import { useRun } from "@/lib/use-run";

import { StatusChip } from "../StatusChip";
import { Button, Card, ErrorText, Spinner } from "../ui";
import { CvPreview, LetterPreview } from "./Documents";
import { EvidenceTable, FitScore } from "./EvidenceTable";
import { ApprovalControls, LowFitQuestion, TextQuestion } from "./Questions";
import { VerifierPanel } from "./VerifierPanel";

export function RunDetail({ runId }: { runId: string }) {
  const agent = useAgent();
  const { run, error, busy, act } = useRun(runId);
  const evidence = useEvidence();

  if (!run) return error ? <ErrorText>{error}</ErrorText> : <Spinner label="Loading…" />;
  const answer = (value: Record<string, unknown>) => act(() => agent.answer(runId, value));

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <div className="flex flex-wrap items-center gap-3">
          <StatusChip status={run.status} />
          {run.posting?.company && <span className="text-sm text-muted">{run.posting.company}</span>}
        </div>
        <h1 className="font-serif text-4xl">{run.posting?.title ?? "New application"}</h1>
      </header>

      {error && <ErrorText>{error}</ErrorText>}
      <NextStep run={run} busy={busy} onAnswer={answer} onRetry={() => act(() => agent.retry(runId))} />

      {run.fit && (
        <Card>
          <div className="mb-4 flex flex-wrap items-end justify-between gap-4">
            <h2 className="font-serif text-2xl">Fit</h2>
            <FitScore score={run.fit.score} />
          </div>
          <p className="mb-4 text-sm text-muted">{run.fit.summary}</p>
          <EvidenceTable fit={run.fit} posting={run.posting} evidence={evidence} />
        </Card>
      )}

      {(run.cv || run.cover_letter) && (
        <div className="grid gap-6 lg:grid-cols-2">
          {run.cv && (
            <Card>
              <h2 className="mb-3 font-serif text-2xl">CV</h2>
              <CvPreview cv={run.cv} evidence={evidence} />
            </Card>
          )}
          {run.cover_letter && (
            <Card>
              <h2 className="mb-3 font-serif text-2xl">Cover letter</h2>
              <LetterPreview letter={run.cover_letter} evidence={evidence} />
            </Card>
          )}
        </div>
      )}

      {run.verification_history.length > 0 && (
        <Card>
          <h2 className="mb-3 font-serif text-2xl">Fact-check</h2>
          <VerifierPanel history={run.verification_history} />
        </Card>
      )}

      <UsageLine run={run} />
    </div>
  );
}

function NextStep({
  run,
  busy,
  onAnswer,
  onRetry,
}: {
  run: RunView;
  busy: boolean;
  onAnswer: (value: Record<string, unknown>) => void;
  onRetry: () => void;
}) {
  const agent = useAgent();
  const w = run.waiting_for;

  if (run.status === "running") {
    return <Spinner label={`${STEP_LABEL[run.step ?? ""] ?? "Working"}…`} />;
  }
  if (run.status === "error") {
    return (
      <Card className="space-y-3 border-terracotta">
        <p className="font-medium">A step failed</p>
        <p className="font-mono text-xs text-muted">{run.error}</p>
        <Button onClick={onRetry} disabled={busy}>
          Retry
        </Button>
      </Card>
    );
  }
  if (run.status === "stopped") {
    return <p className="text-muted">Stopped: you decided not to apply.</p>;
  }
  if (run.status === "done") {
    return (
      <Card className="space-y-3">
        <p className="font-medium">Your documents are ready.</p>
        <div className="flex flex-wrap gap-3">
          {run.files.cv && (
            <a className="rounded-md bg-ink px-4 py-2 text-sm text-paper hover:bg-terracotta" href={agent.fileUrl(run.run_id, "cv")}>
              Download CV
            </a>
          )}
          {run.files.cover_letter && (
            <a
              className="rounded-md border border-ink px-4 py-2 text-sm hover:bg-ink hover:text-paper"
              href={agent.fileUrl(run.run_id, "cover_letter")}
            >
              Download cover letter
            </a>
          )}
        </div>
      </Card>
    );
  }
  if (!w) return null;

  return (
    <Card className="border-terracotta">
      {w.type === "clarify" && (
        <TextQuestion
          label={w.question ?? "Tell the agent more about this role"}
          hint="The posting is too vague to tailor an application."
          field="answer"
          busy={busy}
          onAnswer={onAnswer}
        />
      )}
      {w.type === "paste_text" && (
        <TextQuestion
          label="Posting text"
          hint={`The URL could not be read: ${w.reason}`}
          field="text"
          multiline
          busy={busy}
          onAnswer={onAnswer}
        />
      )}
      {w.type === "low_fit" && (
        <LowFitQuestion {...w} posting={run.posting} busy={busy} onAnswer={onAnswer} />
      )}
      {w.type === "approve" && (
        <div className="space-y-3">
          <p className="font-medium">Review the fit, the CV and the cover letter below.</p>
          <ApprovalControls busy={busy} onAnswer={onAnswer} />
        </div>
      )}
    </Card>
  );
}

function UsageLine({ run }: { run: RunView }) {
  const u = run.usage;
  if (u.calls.length === 0) return null;
  return (
    <p className="font-mono text-xs text-muted">
      {u.calls.length} AI calls · {u.total_latency_s.toFixed(0)} s · {formatCost(u.total_cost_usd)}
    </p>
  );
}
