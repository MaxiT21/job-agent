// Friendly aliases over the generated OpenAPI types (src/lib/api-types.ts — do not edit that file).
import type { components } from "./api-types";

type S = components["schemas"];

export type RunView = S["RunView"];
export type RunSummary = S["RunSummary"];
export type RunStatus = RunView["status"];
export type WaitingFor = NonNullable<RunView["waiting_for"]>;
export type StartRun = S["StartRun"];
export type Application = S["Application"];
export type ApplicationStatus = Application["status"];
export type Profile = S["Profile"];
export type ProfileItem = S["ProfileItem"];
export type ProfileView = S["ProfileView"];
export type ProfileDraft = S["ProfileDraft"];
export type DraftFlag = S["DraftFlag"];
export type GuidedSection = S["GuidedSection"];
export type JobPosting = S["JobPosting"];
export type FitReport = S["FitReport"];
export type RequirementMatch = S["RequirementMatch"];
export type TailoredCV = S["TailoredCV"];
export type CoverLetter = S["CoverLetter"];
export type GroundedLine = S["GroundedLine"];
export type VerificationResult = S["VerificationResult"];
export type FileKind = "cv" | "cover_letter";
