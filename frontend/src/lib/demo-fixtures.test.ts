// @vitest-environment node
// The public demo must only ever contain the fictional sample candidate.
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const DEMO = join(__dirname, "../../public/demo");
const SAMPLE = readFileSync(join(__dirname, "../../../backend/data/profile.sample.yaml"), "utf8");
const sampleName = SAMPLE.match(/^name: (.+)$/m)![1].trim();
const files = readdirSync(DEMO).filter((f) => f.endsWith(".json") && f !== "index.json");

describe("demo recordings", () => {
  it("exist", () => {
    expect(files.length).toBeGreaterThanOrEqual(3);
  });

  it.each(files)("%s uses only the sample profile", (file) => {
    const text = readFileSync(join(DEMO, file), "utf8");
    const rec = JSON.parse(text);
    expect(rec.profile.name).toBe(sampleName);
    expect(text).not.toMatch(/\/Users\/|\/home\/|outputs\/runs/); // no local paths
  });
});
