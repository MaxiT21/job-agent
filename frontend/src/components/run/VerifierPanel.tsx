import type { VerificationResult } from "@/lib/types";

function summary(history: VerificationResult[]): string {
  const caught = history.filter((v) => !v.passed).reduce((n, v) => n + v.issues.length, 0);
  const last = history.at(-1);
  if (!last) return "Not checked yet.";
  if (last.passed && caught === 0) return "Every line is supported by your profile. Passed on the first check.";
  if (last.passed)
    return `Caught ${caught} issue${caught === 1 ? "" : "s"} in earlier drafts and had them rewritten. Final check passed.`;
  return `${last.issues.length} line${last.issues.length === 1 ? "" : "s"} still flagged after retries — review them before approving.`;
}

/** Every verification pass: what was caught, and whether the final draft passed. */
export function VerifierPanel({ history }: { history: VerificationResult[] }) {
  return (
    <section aria-label="Fact-check" className="space-y-3">
      <p className="text-sm">{summary(history)}</p>
      <ol className="space-y-2">
        {history.map((v, i) => (
          <li key={i} className="text-sm">
            <span className={`font-mono text-xs uppercase ${v.passed ? "text-met" : "text-gap"}`}>
              Pass {i + 1}: {v.passed ? "passed" : `${v.issues.length} flagged`}
            </span>
            {v.issues.length > 0 && (
              <ul className="mt-1 space-y-1 border-l-2 border-line pl-3">
                {v.issues.map((issue, j) => (
                  <li key={j}>
                    <span className="text-muted">“{issue.text}”</span> — {issue.reason}{" "}
                    <span className="font-mono text-[11px] text-muted">({issue.where})</span>
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}
