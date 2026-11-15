// What every screen needs from "the agent". Two implementations:
//  - HttpClient: the real backend through the same-origin /api proxy (private app)
//  - DemoClient: recorded runs bundled with the site (public demo, no backend)
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

export interface AgentClient {
  readonly demo: boolean;
  me(): Promise<boolean>;
  login(password: string): Promise<void>;
  logout(): Promise<void>;

  listRuns(): Promise<RunSummary[]>;
  startRun(input: StartRun): Promise<RunView>;
  getRun(id: string): Promise<RunView>;
  answer(id: string, value: Record<string, unknown>): Promise<RunView>;
  retry(id: string): Promise<RunView>;
  fileUrl(id: string, kind: FileKind): string;

  listApplications(): Promise<Application[]>;
  updateApplication(runId: string, status: ApplicationStatus): Promise<Application>;

  getProfile(): Promise<ProfileView>;
  saveProfile(profile: Profile): Promise<ProfileView>;
  getQuestions(): Promise<GuidedSection[]>;
  getAnswers(): Promise<Record<string, string>>;
  saveAnswers(answers: Record<string, string>): Promise<void>;
  draftProfile(answers: Record<string, string>): Promise<ProfileDraft>;
}
