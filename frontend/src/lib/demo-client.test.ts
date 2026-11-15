import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { profile, run } from "@/test/fixtures";

import { DemoClient, type Recording } from "./demo-client";
import { ApiError } from "./http-client";

const lowFitView = run({
  waiting_for: { type: "low_fit", score: 30, gaps: ["r3"], summary: "Weak" },
  cv: null,
  cover_letter: null,
});

const recordings: Record<string, Recording> = {
  "strong-match": {
    id: "strong-match",
    title: "Strong match",
    description: "d",
    posting_text: "posting",
    profile,
    steps: [
      { view: run({ run_id: "strong-match" }), answer: { approved: true } },
      {
        view: run({ run_id: "strong-match", status: "done", waiting_for: null, files: { cv: true, cover_letter: true } }),
        answer: null,
      },
    ],
  },
  "low-fit": {
    id: "low-fit",
    title: "Low fit",
    description: "d",
    posting_text: "posting",
    profile,
    steps: [
      { view: { ...lowFitView, run_id: "low-fit" }, answer: { proceed: true } },
      { view: run({ run_id: "low-fit" }), answer: { approved: true } },
    ],
  },
};
const index = {
  scenarios: Object.values(recordings).map(({ id, title, description }) => ({ id, title, description })),
  questions: [{ id: "basics", title: "About you", prompt: "p", hints: ["h"], optional: false }],
};

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const name = url.split("/").pop()!.replace(".json", "");
      const body = name === "index" ? index : recordings[name];
      return new Response(JSON.stringify(body), { status: body ? 200 : 404 });
    }),
  );
});
afterEach(() => vi.unstubAllGlobals());

describe("DemoClient", () => {
  it("replays a recording: working, then each recorded pause", async () => {
    const demo = new DemoClient("/demo", 1);

    const first = await demo.getRun("strong-match");
    expect(first.status).toBe("running");
    expect(first.step).toBe("extract_requirements");
    expect((await demo.getRun("strong-match")).waiting_for?.type).toBe("approve");

    expect((await demo.answer("strong-match", { approved: true })).status).toBe("running");
    const done = await demo.getRun("strong-match");
    expect(done.status).toBe("done");
    expect(demo.fileUrl("strong-match", "cv")).toBe("/demo/strong-match/cv.docx");
  });

  it("stops when the visitor declines a low fit", async () => {
    const demo = new DemoClient("/demo", 0);
    await demo.getRun("low-fit");
    const stopped = await demo.answer("low-fit", { proceed: false });
    expect(stopped.status).toBe("stopped");
    expect((await demo.getRun("low-fit")).status).toBe("stopped");
  });

  it("explains that unrecorded paths need the live agent", async () => {
    const demo = new DemoClient("/demo", 0);
    await demo.getRun("strong-match");
    await expect(demo.answer("strong-match", { approved: false, notes: "x" })).rejects.toBeInstanceOf(ApiError);
    await expect(demo.startRun({ posting_text: "x" })).rejects.toThrow(/live agent/i);
    await expect(demo.draftProfile({})).rejects.toThrow(/live agent/i);
  });

  it("serves the sample profile, the questions and a tracker of the scenarios", async () => {
    const demo = new DemoClient("/demo", 0);
    expect((await demo.getProfile()).profile.name).toBe("Alex Example");
    expect((await demo.getQuestions())[0].id).toBe("basics");
    const apps = await demo.listApplications();
    expect(apps.map((a) => a.run_id)).toEqual(["strong-match", "low-fit"]);
    const updated = await demo.updateApplication("low-fit", "interview");
    expect(updated.status).toBe("interview");
    expect(await demo.me()).toBe(true);
  });
});
