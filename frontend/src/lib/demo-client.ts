// The public demo: replays runs recorded with the real agent on the fictional sample profile
// (backend/scripts/record_demo.py → public/demo/*.json). No backend, no keys, no AI calls.
import type { AgentClient } from "./client";
import { ApiError } from "./http-client";
import type {
  Application,
  ApplicationStatus,
  FileKind,
  GuidedSection,
  Profile,
  ProfileDraft,
  ProfileView,
  RunSummary,
  RunView,
  StartRun,
} from "./types";

export type Recording = {
  id: string;
  title: string;
  description: string;
  posting_text: string;
  profile: Profile;
  steps: { view: RunView; answer: Record<string, unknown> | null }[];
};

export type DemoScenario = { id: string; title: string; description: string };
type DemoIndex = { scenarios: DemoScenario[]; questions: GuidedSection[] };

const LIVE_ONLY = "This needs the live agent. The public demo replays recorded runs only.";

/** LLM step name → the graph node shown in the progress line. */
const NODE_FOR_STEP: Record<string, string> = {
  extract: "extract_requirements",
  match: "match_profile",
  tailor_cv: "tailor_cv",
  cover_letter: "write_cover_letter",
  verify: "verify",
};

type RunState = { position: number; pendingPolls: number; stopped: boolean };

export class DemoClient implements AgentClient {
  readonly demo = true;
  private indexPromise?: Promise<DemoIndex>;
  private recordings = new Map<string, Promise<Recording>>();
  private runs = new Map<string, RunState>();
  private statuses = new Map<string, ApplicationStatus>();

  /** `runningPolls`: how many polls show "working" before the next recorded pause. */
  constructor(
    private readonly base = "/demo",
    private readonly runningPolls = 2,
  ) {}

  private async json<T>(path: string): Promise<T> {
    const res = await fetch(`${this.base}/${path}`);
    if (!res.ok) throw new ApiError(404, "Unknown demo scenario");
    return res.json();
  }

  index(): Promise<DemoIndex> {
    return (this.indexPromise ??= this.json<DemoIndex>("index.json"));
  }

  async scenarios(): Promise<DemoScenario[]> {
    return (await this.index()).scenarios;
  }

  private recording(id: string): Promise<Recording> {
    let rec = this.recordings.get(id);
    if (!rec) {
      rec = this.json<Recording>(`${encodeURIComponent(id)}.json`);
      this.recordings.set(id, rec);
    }
    return rec;
  }

  private state(id: string): RunState {
    let s = this.runs.get(id);
    if (!s) {
      s = { position: 0, pendingPolls: this.runningPolls, stopped: false };
      this.runs.set(id, s);
    }
    return s;
  }

  /** What the run looks like while "working" towards step `position`. */
  private working(rec: Recording, s: RunState): RunView {
    const target = rec.steps[s.position].view;
    const before = s.position > 0 ? rec.steps[s.position - 1].view : null;
    const newCalls = target.usage.calls.slice(before?.usage.calls.length ?? 0);
    // Poll k of `runningPolls` (1-based) shows the k-th slice of the calls made for this step.
    const k = this.runningPolls - s.pendingPolls;
    const idx = Math.floor(((k - 1) * newCalls.length) / Math.max(this.runningPolls, 1));
    const step = NODE_FOR_STEP[newCalls[idx]?.step ?? "extract"] ?? "extract_requirements";
    const shown = before ?? {
      ...target,
      posting: null,
      fit: null,
      cv: null,
      cover_letter: null,
      verification: null,
      verification_history: [],
      usage: { calls: [], total_cost_usd: 0, total_latency_s: 0 },
    };
    return {
      ...shown,
      status: "running",
      step,
      waiting_for: null,
      files: { cv: false, cover_letter: false },
    };
  }

  private async current(id: string): Promise<RunView> {
    const rec = await this.recording(id);
    const s = this.state(id);
    const view = rec.steps[s.position].view;
    if (s.stopped) return { ...view, status: "stopped", waiting_for: null };
    if (s.pendingPolls > 0) {
      s.pendingPolls -= 1;
      return this.working(rec, s);
    }
    return view;
  }

  async me() {
    return true;
  }
  async login() {}
  async logout() {}

  async listRuns(): Promise<RunSummary[]> {
    const out: RunSummary[] = [];
    for (const id of this.runs.keys()) {
      const rec = await this.recording(id);
      const view = rec.steps[this.state(id).position].view;
      out.push({
        run_id: id,
        created_at: null,
        status: this.state(id).stopped ? "stopped" : view.status,
        company: view.posting?.company ?? null,
        title: view.posting?.title ?? rec.title,
        fit_score: view.fit?.score ?? null,
      });
    }
    return out;
  }

  async startRun(_input: StartRun): Promise<RunView> {
    throw new ApiError(400, LIVE_ONLY);
  }

  getRun(id: string) {
    return this.current(id);
  }

  async answer(id: string, value: Record<string, unknown>): Promise<RunView> {
    const rec = await this.recording(id);
    const s = this.state(id);
    const step = rec.steps[s.position];
    const type = step.view.waiting_for?.type;
    if (type === "low_fit" && value.proceed === false) {
      s.stopped = true;
      return this.current(id);
    }
    if (type === "approve" && value.approved === false) {
      throw new ApiError(400, "Requesting changes needs the live agent. In the demo, approve to see the documents.");
    }
    if (!step.answer || s.position + 1 >= rec.steps.length) throw new ApiError(409, "Nothing to answer");
    s.position += 1;
    s.pendingPolls = this.runningPolls;
    return this.current(id);
  }

  async retry(): Promise<RunView> {
    throw new ApiError(400, LIVE_ONLY);
  }

  fileUrl(id: string, kind: FileKind) {
    return `${this.base}/${encodeURIComponent(id)}/${kind}.docx`;
  }

  async listApplications(): Promise<Application[]> {
    const apps: Application[] = [];
    for (const { id } of await this.scenarios()) {
      const rec = await this.recording(id);
      const last = rec.steps.at(-1)!.view;
      if (!last.posting || !last.fit) continue;
      apps.push({
        run_id: id,
        created_at: new Date().toISOString(),
        company: last.posting.company,
        title: last.posting.title,
        location: last.posting.location ?? null,
        fit_score: last.fit.score,
        cv_path: this.fileUrl(id, "cv"),
        letter_path: this.fileUrl(id, "cover_letter"),
        status: this.statuses.get(id) ?? "ready",
      });
    }
    return apps;
  }

  async updateApplication(runId: string, status: ApplicationStatus): Promise<Application> {
    this.statuses.set(runId, status);
    const app = (await this.listApplications()).find((a) => a.run_id === runId);
    if (!app) throw new ApiError(404, "Application not found");
    return app;
  }

  async getProfile(): Promise<ProfileView> {
    const [first] = await this.scenarios();
    return { source: "sample", profile: (await this.recording(first.id)).profile };
  }
  async saveProfile(_profile: Profile): Promise<ProfileView> {
    throw new ApiError(400, LIVE_ONLY);
  }
  async getQuestions(): Promise<GuidedSection[]> {
    return (await this.index()).questions;
  }
  async getAnswers() {
    return {};
  }
  async saveAnswers() {}
  async draftProfile(_answers: Record<string, string>): Promise<ProfileDraft> {
    throw new ApiError(400, LIVE_ONLY);
  }
}
