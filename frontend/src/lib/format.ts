import type { RunStatus } from "./types";

export const STATUS_LABEL: Record<RunStatus, string> = {
  running: "Working",
  waiting: "Needs you",
  done: "Done",
  stopped: "Stopped",
  error: "Error",
};

/** Human wording for the graph node a run is executing. */
export const STEP_LABEL: Record<string, string> = {
  fetch_posting: "Reading the posting",
  ask_for_text: "Waiting for the posting text",
  extract_requirements: "Extracting requirements",
  ask_clarification: "Waiting for your answer",
  match_profile: "Matching your profile",
  confirm_low_fit: "Waiting for your decision",
  tailor_cv: "Tailoring your CV",
  write_cover_letter: "Writing the cover letter",
  verify: "Fact-checking every line",
  human_approval: "Waiting for your review",
  render_and_log: "Creating the documents",
};

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

export function formatCost(usd: number): string {
  return usd < 0.01 ? `$${usd.toFixed(4)}` : `$${usd.toFixed(2)}`;
}
