import type { AgentClient } from "./client";
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

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class UnauthorizedError extends ApiError {
  constructor(message = "Not logged in") {
    super(401, message);
    this.name = "UnauthorizedError";
  }
}

type ValidationDetail = { loc?: (string | number)[]; msg?: string };

function describe(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: ValidationDetail) => {
        const field = (d.loc ?? []).filter((p) => p !== "body").join(".");
        return field ? `${field}: ${d.msg}` : (d.msg ?? "");
      })
      .join("; ");
  }
  return fallback;
}

export class HttpClient implements AgentClient {
  readonly demo = false;

  constructor(private readonly base = "/api") {}

  private async request<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
    const res = await fetch(`${this.base}${path}`, {
      method: init.method ?? "GET",
      credentials: "same-origin",
      headers: init.body === undefined ? {} : { "content-type": "application/json" },
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
    });
    const text = await res.text();
    const data = text ? JSON.parse(text) : undefined;
    if (res.status === 401) throw new UnauthorizedError(describe(data?.detail, "Not logged in"));
    if (!res.ok) throw new ApiError(res.status, describe(data?.detail, res.statusText));
    return data as T;
  }

  async me() {
    return (await this.request<{ authenticated: boolean }>("/auth/me")).authenticated;
  }
  login(password: string) {
    return this.request<void>("/auth/login", { method: "POST", body: { password } });
  }
  logout() {
    return this.request<void>("/auth/logout", { method: "POST" });
  }

  listRuns() {
    return this.request<RunSummary[]>("/runs");
  }
  startRun(input: StartRun) {
    return this.request<RunView>("/runs", { method: "POST", body: input });
  }
  getRun(id: string) {
    return this.request<RunView>(`/runs/${encodeURIComponent(id)}`);
  }
  answer(id: string, value: Record<string, unknown>) {
    return this.request<RunView>(`/runs/${encodeURIComponent(id)}/resume`, {
      method: "POST",
      body: { value },
    });
  }
  retry(id: string) {
    return this.request<RunView>(`/runs/${encodeURIComponent(id)}/retry`, { method: "POST" });
  }
  fileUrl(id: string, kind: FileKind) {
    return `${this.base}/runs/${encodeURIComponent(id)}/files/${kind}`;
  }

  listApplications() {
    return this.request<Application[]>("/applications");
  }
  updateApplication(runId: string, status: ApplicationStatus) {
    return this.request<Application>(`/applications/${encodeURIComponent(runId)}`, {
      method: "PATCH",
      body: { status },
    });
  }

  getProfile() {
    return this.request<ProfileView>("/profile");
  }
  saveProfile(profile: Profile) {
    return this.request<ProfileView>("/profile", { method: "PUT", body: profile });
  }
  getQuestions() {
    return this.request<GuidedSection[]>("/profile/questions");
  }
  getAnswers() {
    return this.request<Record<string, string>>("/profile/answers");
  }
  saveAnswers(answers: Record<string, string>) {
    return this.request<void>("/profile/answers", { method: "PUT", body: answers });
  }
  draftProfile(answers: Record<string, string>) {
    return this.request<ProfileDraft>("/profile/draft", { method: "POST", body: { answers } });
  }
}
