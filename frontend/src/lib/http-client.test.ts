import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, HttpClient, UnauthorizedError } from "./http-client";

function mockFetch(status: number, body: unknown) {
  const fn = vi.fn().mockResolvedValue(
    new Response(body === undefined ? null : JSON.stringify(body), {
      status,
      headers: { "content-type": "application/json" },
    }),
  );
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => vi.unstubAllGlobals());

describe("HttpClient", () => {
  it("calls the same-origin /api proxy with credentials", async () => {
    const fetch = mockFetch(200, []);
    await new HttpClient().listRuns();
    expect(fetch).toHaveBeenCalledWith(
      "/api/runs",
      expect.objectContaining({ credentials: "same-origin" }),
    );
  });

  it("sends JSON bodies", async () => {
    const fetch = mockFetch(202, { run_id: "r1", status: "running" });
    await new HttpClient().startRun({ posting_text: "x".repeat(60) });
    const [, init] = fetch.mock.calls[0];
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ posting_text: "x".repeat(60) });
    expect(init.headers["content-type"]).toBe("application/json");
  });

  it("turns 401 into UnauthorizedError", async () => {
    mockFetch(401, { detail: "Not logged in" });
    await expect(new HttpClient().listRuns()).rejects.toBeInstanceOf(UnauthorizedError);
  });

  it("turns other errors into ApiError with the server's detail", async () => {
    mockFetch(409, { detail: "The run is still working; wait until it pauses" });
    const err = await new HttpClient().retry("r1").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(409);
    expect(err.message).toBe("The run is still working; wait until it pauses");
  });

  it("formats FastAPI validation errors readably", async () => {
    mockFetch(422, { detail: [{ loc: ["body", "proceed"], msg: "Field required" }] });
    const err = await new HttpClient().answer("r1", {}).catch((e) => e);
    expect(err.message).toBe("proceed: Field required");
  });

  it("handles empty 204 responses", async () => {
    mockFetch(204, undefined);
    await expect(new HttpClient().logout()).resolves.toBeUndefined();
  });
});
